import json
import os
import threading
import time
from typing import Any

import redis


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


def wrap_sync(
    obj: list | dict, parent, topmost_key: str
):
    """Wrap an object to synchronize its attributes with Redis."""
    if isinstance(obj, dict):
        return SyncedDict(obj, parent, topmost_key)
    elif isinstance(obj, list):
        return SyncedList(obj, parent, topmost_key)
    return obj


class MemoryBase:
    """A synchronized key-value store that uses a Redis-compatible backend
    (Redis or DragonflyDB) as shared memory. If the backend is unavailable,
    values are cached locally and queued for later syncing.

    Environment Variables:
    ----------------------
    - REDIS_HOST:   Hostname of the backend server (default: 'localhost')
    - REDIS_PORT:   Port of the backend server (default: 6379)
    - REDIS_PREFIX: Prefix to use for keys (default: 'memory:')

    Attributes:
    -----------
    _timeout : float
        Timeout for backend operations in seconds (default: 0.5).
    _queue : list
        Queue of (key, value) tuples to be synced when the backend becomes
        available.
    _attributes : dict
        Local cache of attributes (always up-to-date with the last set values).

    Examples:
    ---------
    >>> os.environ['REDIS_HOST'] = 'localhost'
    >>> os.environ['REDIS_PORT'] = '6379'

    >>> mem1 = MemoryBase(backend_hostname='localhost')
    >>> mem1.foo = 42
    >>> mem2 = MemoryBase(backend_hostname='localhost')
    >>> print(mem2.foo)
    42

    >>> mem1.bar = {"a": 1}
    >>> print(mem2.bar)
    {'a': 1}
    """

    def __init__(
        self,
        backend_hostname: str,
        backend_port: int = 6379,
        backend_prefix: str = "memory:",
    ):
        """Initialize the Memory instance and flush any queued updates."""
        self._host = os.environ.get("REDIS_HOST", backend_hostname)
        self._port = int(os.environ.get("REDIS_PORT", backend_port))
        self._prefix = backend_prefix
        self._timeout = 0.5  # Seconds

        self._queue = []
        self._attributes = {}
        self._last_modified = {}  # Track last modified timestamps

        self._stop_event = threading.Event()
        self._thread = None

        self._redis_available = (
            False  # owned exclusively by the background thread
        )
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
                        break  # Never connected; give up.
                    time.sleep(1)

        self.stop_background_flush()

    def _connect(self):
        """Establish a new Redis connection.

        Returns:
            redis.Redis or None: A Redis client if connection works;
            otherwise None.
        """
        client = redis.Redis(
            host=self._host,
            port=self._port,
            socket_connect_timeout=self._timeout,
            socket_timeout=self._timeout,
        )
        client.ping()
        return client

    def _key(self, name):
        """Generate Redis key with prefix."""
        return f"{self._prefix}{name}"

    def _flush_queue(self):
        """Attempt one flush of the queue to the backend.

        Connects once; raises on failure so the caller can apply backoff. For
        each queued item, skips writes where the backend already holds a newer
        timestamp.
        """
        client = self._connect()  # raises on failure
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

        On each cycle this thread attempts to connect and flush any
        queued writes. Success sets _redis_available = True and resets
        the backoff to 1 s. Failure sets _redis_available = False and
        doubles the wait (capped at 30 s), so the main thread can fall
        back to local cache without blocking.
        """
        backoff = 1
        while not self._stop_event.is_set():
            try:
                self._flush_queue()  # raises on connection failure
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

        Store in the backend if available, otherwise queue it.

        Raises:
            ValueError: If the value is not serializable.
        """
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        try:
            _ = json.dumps(value)
        except json.JSONDecodeError:
            raise

        self._set(name, value)

    def _write_to_redis_or_queue(self, name: str, payload: dict):
        """Write to the backend if available; queue for later if not.

        On a connection failure the flag is cleared so subsequent calls skip
        the attempt until the background thread re-establishes the connection.
        """
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
        """Update local cache and write through to the backend (or queue if
        down)."""
        self._attributes[name] = wrap_sync(value, self, name)
        timestamp = time.time_ns()
        self._last_modified[name] = timestamp
        self._write_to_redis_or_queue(
            name, {"value": value, "last_modified": timestamp}
        )

    def __getattr__(self, name: str) -> Any:
        """Return the attribute, reading from the backend when available.

        Falls back to local cache when the backend is down so the main thread
        never blocks.

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
                # Backend is up but key not there yet (still in queue);
                # fall through to local cache.
            except Exception:
                self._redis_available = False

        if name in self._attributes:
            return self._attributes[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def sync(self, name: str):
        """Write the current local value of an attribute to the backend (or
        queue if down)."""
        if name not in self._attributes:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

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
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

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
    """MemoryBase subclass that namespaces keys by a custom prefix.

    Args:
        prefix (str): Scope prefix to isolate this Memory instance's keys.
        backend_hostname (str): Backend host.
        backend_port (int): Backend port (default 6379).
        backend_prefix (str): Base prefix for keys (default 'memory:').
    """

    def __init__(
        self,
        prefix: str,
        backend_hostname: str,
        backend_port: int = 6379,
        backend_prefix: str = "memory:",
    ):
        self._prefix_id = prefix
        super().__init__(
            backend_hostname=backend_hostname,
            backend_port=backend_port,
            backend_prefix=backend_prefix,
        )

    def _key(self, name):
        # Override to include prefix_id in the key
        return f"{self._prefix}{self._prefix_id}:{name}"
