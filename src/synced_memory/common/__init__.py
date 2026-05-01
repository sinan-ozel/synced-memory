import json
import os
import threading
import time
from typing import Any


class SyncedList(list):

    def __init__(self, iterable, parent, topmost_key: str):
        for i, item in enumerate(iterable):
            iterable[i] = wrap_sync(item, self, f"{topmost_key}[{i}]")
        super().__init__(iterable)
        self._parent = parent
        self._topmost_key = topmost_key

    def append(self, item):
        super().append(item)
        self._parent.sync(self._topmost_key)

    def extend(self, iterable):
        super().extend(iterable)
        self._parent.sync(self._topmost_key)

    def insert(self, index, item):
        super().insert(index, item)
        self._parent.sync(self._topmost_key)

    def remove(self, item):
        super().remove(item)
        self._parent.sync(self._topmost_key)

    def sync(self, name: str):
        self._parent.sync(self._topmost_key)

    def aslist(self):
        """Return a plain Python list, recursively converting nested
        SyncedList/SyncedDict objects."""
        result = []
        for item in self:
            if isinstance(item, SyncedList):
                result.append(item.aslist())
            elif isinstance(item, SyncedDict):
                result.append(item.asdict())
            else:
                result.append(item)
        return result


class SyncedDict(dict):

    def __init__(self, mapping, parent, topmost_key: str):
        for k, v in mapping.items():
            mapping[k] = wrap_sync(v, self, topmost_key)
        super().__init__(mapping)
        self._parent = parent
        self._topmost_key = topmost_key

    def __setitem__(self, k, v):
        super().__setitem__(k, v)
        self._parent.sync(self._topmost_key)

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._parent.sync(self._topmost_key)

    def sync(self, name: str):
        self._parent.sync(self._topmost_key)

    def asdict(self):
        """Return a plain Python dict, recursively converting nested
        SyncedList/SyncedDict objects."""
        result = {}
        for key, value in self.items():
            if isinstance(value, SyncedList):
                result[key] = value.aslist()
            elif isinstance(value, SyncedDict):
                result[key] = value.asdict()
            else:
                result[key] = value
        return result


def wrap_sync(obj: list | dict, parent, topmost_key: str):
    """Wrap an object to synchronize its attributes with the backend."""
    if isinstance(obj, dict):
        return SyncedDict(obj, parent, topmost_key)
    elif isinstance(obj, list):
        return SyncedList(obj, parent, topmost_key)
    return obj


class MemoryBase:
    """A synchronized key-value store backed by a Redis-compatible server.

    If the backend is unavailable, values are cached locally and queued for
    syncing when it comes back online.

    Environment Variables:
    ----------------------
    - REDIS_HOST:  Hostname of the backend server
    - REDIS_PORT:  Port of the backend server

    Attributes:
    -----------
    _timeout : float
        Timeout for backend operations in seconds (default: 0.5).
    _queue : list
        Queue of (key, value) tuples to be synced when backend is available.
    _attributes : dict
        Local cache of attributes.
    """

    def __init__(
        self,
        backend_hostname: str = "redis",
        backend_port: int = 6379,
        backend_prefix: str = "memory:",
    ):
        """Initialize the MemoryBase instance and flush any queued updates."""
        self._host = os.environ.get("REDIS_HOST", backend_hostname)
        self._port = int(os.environ.get("REDIS_PORT", backend_port))
        self._prefix = backend_prefix
        self._timeout = 0.5  # Seconds

        self._queue = []
        self._attributes = {}
        self._last_modified = {}

        self._stop_event = threading.Event()
        self._thread = None

        self._redis_available = False
        self._is_connected_to_redis_at_least_once = False

        self.start_background_flush()
        self._load_from_redis()

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Flush any remaining queue then stop the background thread."""
        if self._queue:
            while True:
                try:
                    self._flush_queue()
                    break
                except Exception:
                    if not self._is_connected_to_redis_at_least_once:
                        break
                    time.sleep(1)

        self.stop_background_flush()

    def _connect(self):
        """Establish a new backend connection.

        Returns:
            redis.Redis: A client if connection works; raises on failure.
        """
        import redis

        client = redis.Redis(
            host=self._host,
            port=self._port,
            socket_connect_timeout=self._timeout,
            socket_timeout=self._timeout,
        )
        client.ping()
        return client

    def _key(self, name):
        """Generate backend key with prefix."""
        return f"{self._prefix}{name}"

    def _flush_queue(self):
        """Attempt one flush of the queue to the backend.

        Connects once; raises on failure so the caller can apply backoff. For
        each queued item, skips writes where the backend already holds a newer
        timestamp.
        """
        client = self._connect()
        self._is_connected_to_redis_at_least_once = True

        while self._queue:
            key, payload = self._queue.pop(0)
            value = payload.get("value")
            queued_timestamp = payload.get("last_modified")

            raw = client.get(self._key(key))
            redis_timestamp = 0
            if raw is not None:
                obj = json.loads(raw)
                redis_timestamp = obj.get("last_modified", 0)

            if redis_timestamp > queued_timestamp:
                continue

            if value is None:
                client.delete(self._key(key))
            else:
                client.set(self._key(key), json.dumps(payload))

    def _background_flush_loop(self):
        """Own the backend connection state and flush the write queue.

        On each cycle this thread attempts to connect and flush any queued
        writes. Success sets _redis_available = True and resets the backoff to
        1 s. Failure sets _redis_available = False and doubles the wait (capped
        at 30 s), so the main thread can fall back to local cache without
        blocking.
        """
        backoff = 1
        while not self._stop_event.is_set():
            try:
                self._flush_queue()
                self._redis_available = True
                backoff = 1
            except Exception:
                self._redis_available = False
                backoff = min(backoff * 2, 30)
                self._stop_event.wait(backoff)
                continue
            self._stop_event.wait(1)

    def start_background_flush(self):
        """Start the background thread to flush the queue regularly."""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._background_flush_loop, daemon=True
            )
            self._thread.start()

    def stop_background_flush(self):
        """Stop the background flushing thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def _load_from_redis(self):
        """Load all keys with the current prefix from the backend into local
        cache."""
        try:
            client = self._connect()
            self._redis_available = True
            self._is_connected_to_redis_at_least_once = True
            pattern = f"{self._prefix}*"
            for key in client.scan_iter(match=pattern):
                name = key.decode().replace(self._prefix, "", 1)
                try:
                    raw = client.get(key)
                    obj = json.loads(raw)
                    if (
                        isinstance(obj, dict)
                        and "value" in obj
                        and "last_modified" in obj
                    ):
                        self._attributes[name] = obj["value"]
                        self._last_modified[name] = obj["last_modified"]
                    else:
                        self._attributes[name] = obj
                except Exception:
                    pass
        except Exception:
            self._redis_available = False

    def __setattr__(self, name, value):
        """Set an attribute.

        Store in backend if available, otherwise queue it.
                Raises:
                    TypeError: If the value is not JSON-serializable.
        """
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        try:
            _ = json.dumps(value)
        except (TypeError, ValueError):
            raise TypeError(
                f"Value for '{name}' is not JSON-serializable: {type(value)}"
            )

        self._set(name, value)

    def _write_to_redis_or_queue(self, name: str, payload: dict):
        """Write to backend if available; queue for later if not."""
        if self._redis_available:
            try:
                client = self._connect()
                client.set(self._key(name), json.dumps(payload))
                self._is_connected_to_redis_at_least_once = True
                return
            except Exception:
                self._redis_available = False
        self._queue.append((name, payload))

    def _set(self, name: str, value: Any):
        """Update local cache and write through to backend (or queue if
        down)."""
        self._attributes[name] = wrap_sync(value, self, name)
        timestamp = time.time_ns()
        self._last_modified[name] = timestamp
        self._write_to_redis_or_queue(
            name, {"value": value, "last_modified": timestamp}
        )

    def __getattr__(self, name: str) -> Any:
        """Return the attribute, reading from backend when available.

        Raises:
            AttributeError: If the attribute has not been set.
        """
        if name.startswith("_"):
            return super().__getattribute__(name)

        if self._redis_available:
            try:
                client = self._connect()
                raw = client.get(self._key(name))
                if raw is not None:
                    self._is_connected_to_redis_at_least_once = True
                    obj = json.loads(raw)
                    value = obj["value"]
                    self._attributes[name] = wrap_sync(value, self, name)
                    self._last_modified[name] = obj["last_modified"]
                    return self._attributes[name]
            except Exception:
                self._redis_available = False

        if name in self._attributes:
            return self._attributes[name]
        raise AttributeError(f"'Memory' object has no attribute '{name}'")

    def sync(self, name: str):
        """Write the current local value of an attribute to backend (or queue
        if down)."""
        if name not in self._attributes:
            raise AttributeError(f"'Memory' object has no attribute '{name}'")

        self._write_to_redis_or_queue(
            name,
            {
                "value": self._attributes[name],
                "last_modified": self._last_modified.get(name, 0),
            },
        )

    def __delattr__(self, name):
        """Remove an attribute from local cache and queue its deletion.

        Raises:
            AttributeError: If the attribute is not found.
        """
        if name.startswith("_"):
            super().__delattr__(name)
            return

        if name not in self._attributes:
            raise AttributeError(f"'Memory' object has no attribute '{name}'")

        del self._attributes[name]
        if name in self._last_modified:
            del self._last_modified[name]

        timestamp = time.time_ns()
        if self._redis_available:
            try:
                client = self._connect()
                client.delete(self._key(name))
                self._is_connected_to_redis_at_least_once = True
                return
            except Exception:
                self._redis_available = False
        self._queue.append((name, {"value": None, "last_modified": timestamp}))


class PrefixedMemoryBase(MemoryBase):
    """MemoryBase subclass that namespaces keys by a scope prefix.

    Args:
        prefix (str): Unique prefix to isolate this scope's memory.
        backend_hostname (str): Backend host.
        backend_port (int): Backend port.
        backend_prefix (str): Base key prefix.
    """

    def __init__(
        self,
        prefix: str,
        backend_hostname: str = "redis",
        backend_port: int = 6379,
        backend_prefix: str = "memory:",
    ):
        self._scope = prefix
        super().__init__(
            backend_hostname=backend_hostname,
            backend_port=backend_port,
            backend_prefix=backend_prefix,
        )

    def _key(self, name):
        return f"{self._prefix}{self._scope}:{name}"


__all__ = [
    "MemoryBase",
    "PrefixedMemoryBase",
    "SyncedList",
    "SyncedDict",
    "wrap_sync",
]
