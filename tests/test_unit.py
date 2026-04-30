import json
import os
import pickle
import tempfile
import time
from copy import deepcopy
from pathlib import Path

import pytest
import redis

from synced_memory.dragonflydb import Memory as MemoryFromDragonfly
from synced_memory.redis import Memory as MemoryFromRedis
from synced_memory.redis import SyncedDict, SyncedList

BACKENDS = [
    pytest.param((MemoryFromRedis, "redis", 6379), id="redis"),
    pytest.param((MemoryFromDragonfly, "dragonflydb", 6379), id="dragonflydb"),
]


@pytest.fixture(params=BACKENDS)
def backend(request):
    return request.param


@pytest.fixture(autouse=True)
def setup_env_and_clear(backend):
    MemoryCls, host, port = backend
    os.environ["REDIS_HOST"] = host
    os.environ["REDIS_PORT"] = str(port)
    mem = MemoryCls()
    client = mem._connect()
    if client:
        keys = client.keys(f"{mem._prefix}*")
        if keys:
            client.delete(*keys)
    yield
    mem = MemoryCls()
    client = mem._connect()
    if client:
        keys = client.keys(f"{mem._prefix}*")
        if keys:
            client.delete(*keys)


@pytest.fixture
def Memory(backend):
    MemoryCls, _, _ = backend
    return MemoryCls


@pytest.fixture
def get_value(backend):
    _, host, port = backend

    def _get(key, prefix="memory:"):
        client = redis.Redis(host=host, port=port)
        raw = client.get(f"{prefix}{key}")
        if raw is not None:
            return json.loads(raw)
        return None

    return _get


def test_set_and_get_scalar(Memory, get_value):
    """Test setting and getting a scalar value across Memory instances."""
    mem1 = Memory()
    mem2 = Memory()
    mem1.answer = 42
    assert mem2.answer == 42
    obj = get_value("answer")
    assert obj["value"] == 42
    assert isinstance(obj["last_modified"], int)
    assert mem1._last_modified["answer"] == obj["last_modified"]


def test_set_and_get_dict(Memory, get_value):
    """Test setting and getting a dictionary value in Memory."""
    mem = Memory()
    expected = {"theme": "dark", "volume": 0.75}
    mem.settings = expected
    assert mem.settings == expected
    obj = get_value("settings")
    assert obj["value"] == expected
    assert isinstance(obj["last_modified"], int)
    assert mem._last_modified["settings"] == obj["last_modified"]


def test_set_and_get_list(Memory, get_value):
    """Test setting and getting a list value in Memory."""
    mem = Memory()
    expected = [1, 2, 3]
    mem.items = expected
    assert mem.items == expected
    obj = get_value("items")
    assert obj["value"] == expected
    assert isinstance(obj["last_modified"], int)
    assert mem._last_modified["items"] == obj["last_modified"]


def test_overwrite_existing_key(Memory, get_value):
    """Test that assigning a new value overwrites the existing key."""
    mem = Memory()
    mem.key = "initial"
    obj1 = get_value("key")
    assert obj1["value"] == "initial"
    mem.key = "updated"
    assert mem.key == "updated"
    obj2 = get_value("key")
    assert obj2["value"] == "updated"
    assert obj2["last_modified"] >= obj1["last_modified"]


def test_missing_attribute_raises(Memory):
    """Test that accessing an unset attribute raises AttributeError."""
    mem = Memory()
    with pytest.raises(AttributeError):
        _ = mem.does_not_exist


def test_internal_attributes_not_stored(Memory):
    """Test that internal attributes are not stored in the backend."""
    mem = Memory()
    assert hasattr(mem, "_host")
    assert "_host" not in mem.__dict__.get("_attributes", {})


def test_multiple_instances_consistency(Memory, get_value):
    """Test that Memory instances share a consistent state."""
    m1 = Memory()
    m2 = Memory()
    m1.shared = {"a": 10}
    assert m2.shared == {"a": 10}
    obj = get_value("shared")
    assert obj["value"] == {"a": 10}
    assert isinstance(obj["last_modified"], int)


def test_attribute_persistence_across_instances(Memory, get_value):
    """Test that attributes persist across new Memory instances."""
    Memory().temp = "hello"
    mem = Memory()
    assert mem.temp == "hello"
    obj = get_value("temp")
    assert obj["value"] == "hello"
    assert isinstance(obj["last_modified"], int)


def test_set_is_non_blocking_when_backend_unavailable(Memory, monkeypatch):
    """Test that writes do not block repeatedly when backend is unavailable.

    After the first failed connection attempt activates the circuit breaker,
    subsequent writes must queue immediately without waiting for the connection
    timeout.
    """
    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")

    mem = Memory()
    mem.warmup = True  # First write: triggers circuit breaker (may block once)

    start = time.time()
    for i in range(10):
        setattr(mem, f"key_{i}", i)
    elapsed = time.time() - start

    assert elapsed < mem._timeout, (
        f"10 writes took {elapsed:.3f}s — expected < {mem._timeout}s. "
        "Writes are still blocking on connection timeout."
    )
    assert all(mem._attributes.get(f"key_{i}") == i for i in range(10))
    assert len(mem._queue) >= 10


def test_queue_flush_when_backend_restored(
    Memory, backend, get_value, monkeypatch
):
    """Test queueing when backend is down and flushing when it's restored."""
    _, host, port = backend

    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")

    mem = Memory()
    mem.foo = "bar"

    assert mem._queue[-1][0] == "foo"
    assert mem._queue[-1][1]["value"] == "bar"
    assert mem.foo == "bar"

    monkeypatch.setenv("REDIS_HOST", host)
    monkeypatch.setenv("REDIS_PORT", str(port))

    mem_restored = Memory(redis_prefix=mem._prefix)
    mem_restored._queue = mem._queue.copy()
    mem_restored._flush_queue()

    obj = get_value("foo")
    assert obj["value"] == "bar"
    assert isinstance(obj["last_modified"], int)


def test_queue_overwrite_before_backend_restored(
    Memory, backend, get_value, monkeypatch
):
    """Test that latest queued value is saved after backend is restored."""
    _, host, port = backend

    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")

    mem = Memory()
    mem.config = {"a": 1}
    mem.config = {"a": 2}

    assert mem.config == {"a": 2}
    assert mem._queue[-1][0] == "config"
    assert mem._queue[-1][1]["value"] == {"a": 2}

    monkeypatch.setenv("REDIS_HOST", host)
    monkeypatch.setenv("REDIS_PORT", str(port))

    mem_restored = Memory(redis_prefix=mem._prefix)
    mem_restored._queue = mem._queue.copy()
    mem_restored._flush_queue()

    obj = get_value("config")
    assert obj["value"] == {"a": 2}
    assert isinstance(obj["last_modified"], int)


@pytest.mark.depends(on=["test_set_and_get_scalar"])
def test_memory_with_custom_prefix(Memory, get_value):
    """Test that Memory with a custom prefix stores and retrieves data
    correctly."""
    custom_prefix = "custom:"
    mem = Memory(redis_prefix=custom_prefix)
    mem.status = "active"
    assert mem.status == "active"

    assert get_value("status", prefix="memory:") is None

    obj = get_value("status", prefix=custom_prefix)
    assert obj["value"] == "active"
    assert isinstance(obj["last_modified"], int)


def test_set_and_delete_attribute(Memory):
    mem = Memory()
    mem.key = "value"
    del mem.key
    with pytest.raises(AttributeError):
        _ = mem.key


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_delete_attribute_queues_if_backend_down(Memory, backend, monkeypatch):
    """Test that deleting an attribute while backend is down queues the
    deletion properly."""
    _, host, port = backend

    monkeypatch.setenv("REDIS_HOST", host)
    monkeypatch.setenv("REDIS_PORT", str(port))
    mem = Memory()
    mem.queued_key = "queued value"

    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")
    mem_down = Memory(redis_prefix=mem._prefix)
    mem_down._attributes = mem._attributes.copy()

    del mem_down.queued_key

    with pytest.raises(AttributeError):
        _ = mem_down.queued_key

    assert any(
        q[0] == "queued_key" and q[1]["value"] is None for q in mem_down._queue
    )


@pytest.mark.depends(
    on=[
        "test_set_and_delete_attribute",
        "test_queue_flush_when_backend_restored",
        "test_queue_overwrite_before_backend_restored",
    ]
)
def test_background_flush_automatically(
    Memory, backend, get_value, monkeypatch
):
    """Test that the background flush loop automatically flushes queued data
    when backend comes back online."""
    _, host, port = backend

    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")
    mem = Memory()

    mem.test_key = "queued_value"

    assert mem._attributes.get("test_key") == "queued_value"
    assert mem._queue[-1][0] == "test_key"
    assert mem._queue[-1][1]["value"] == "queued_value"
    assert mem.test_key == "queued_value"

    monkeypatch.setenv("REDIS_HOST", host)
    monkeypatch.setenv("REDIS_PORT", str(port))

    mem_restored = Memory(redis_prefix=mem._prefix)
    mem_restored._queue = mem._queue.copy()

    time.sleep(2)

    obj = get_value("test_key")
    assert obj["value"] == "queued_value"
    assert isinstance(obj["last_modified"], int)

    del mem.test_key


def test_memory_loads_existing_keys_on_init(Memory):
    """Test that Memory instance loads existing keys on initialization."""
    mem1 = Memory()
    mem1.user = {"name": "Alice", "role": "admin"}

    mem2 = Memory()

    assert "user" in mem2._attributes
    assert mem2.user == {"name": "Alice", "role": "admin"}
    assert isinstance(mem2._last_modified["user"], int)


def test_basic_context_set_and_get(Memory):
    """Test that values set in a `with Memory()` context are correctly
    persisted and can be retrieved in a later context block."""
    with Memory() as memory:
        memory.test_key = "hello world"

    with Memory() as memory:
        assert memory.test_key == "hello world"
        assert isinstance(memory._last_modified["test_key"], int)


def test_context_lifecycle_and_del(Memory):
    """Test that Memory context persists values even after the object is
    deleted, as long as the backend remains available."""
    with Memory() as memory:
        memory.context = "Je me souviens."

    del memory

    with Memory() as memory:
        assert memory.context == "Je me souviens."
        assert isinstance(memory._last_modified["context"], int)


def test_non_serializable_value(Memory):
    """Test that assigning a non-serializable value raises TypeError."""
    with pytest.raises(TypeError):
        with Memory() as memory:
            memory.bad = lambda x: x * 2


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_works_if_backend_never_comes_alive(Memory, backend, monkeypatch):
    """Test that memory works locally even if the backend never connects."""
    _, host, port = backend

    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")
    with Memory() as memory:
        memory.test_key = "hello world"
        assert memory.test_key == "hello world"
        del memory.test_key
        with pytest.raises(AttributeError):
            _ = memory.queued_key

    monkeypatch.setenv("REDIS_HOST", host)
    monkeypatch.setenv("REDIS_PORT", str(port))


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_append_to_list(Memory):
    """Test that appending to a list attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.numbers = [1, 2]
    assert isinstance(mem1.numbers, SyncedList)
    mem1.numbers.append(3)

    mem2 = Memory()
    assert mem2.numbers == [1, 2, 3]


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_insert_to_list(Memory):
    """Test that inserting to a list attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.numbers = [1, 2, 4]
    assert isinstance(mem1.numbers, SyncedList)
    mem1.numbers.insert(2, 3)

    mem2 = Memory()
    assert mem2.numbers == [1, 2, 3, 4]


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_extend_list(Memory):
    """Test that extending a list attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.numbers = [1, 2]
    mem1.numbers.extend([3, 4])

    mem2 = Memory()
    assert mem2.numbers == [1, 2, 3, 4]


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_update_dict(Memory):
    """Test that updating a dict attribute persists across Memory instances."""
    mem1 = Memory()
    mem1.data = {"a": 1}
    assert isinstance(mem1.data, SyncedDict)
    mem1.data.update({"b": 2})

    mem2 = Memory()
    assert mem2.data == {"a": 1, "b": 2}


@pytest.mark.depends(on=["test_update_dict"])
def test_update_dict_in_context(Memory):
    """Test that updating a dict attribute persists across Memory instances."""
    with Memory() as memory:
        memory.data = {"a": 1}
        memory.data.update({"b": 2})

    del memory

    with Memory() as memory:
        assert memory.data == {"a": 1, "b": 2}


@pytest.mark.depends(on=["test_append_to_list"])
def test_append_to_a_nested_list(Memory):
    """Test that appending to a list attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.list_of_lists_of_numbers = [[1, 2], [3, 4]]
    assert isinstance(mem1.list_of_lists_of_numbers, SyncedList)
    assert isinstance(mem1.list_of_lists_of_numbers[1], SyncedList)
    mem1.list_of_lists_of_numbers[1].append(5)

    mem2 = Memory()
    assert mem2.list_of_lists_of_numbers == [[1, 2], [3, 4, 5]]


@pytest.mark.depends(on=["test_update_dict"])
def test_update_nested_dict(Memory):
    """Test that updating a nested dict attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.data = {"a": 1, "b": {"c": 2}}
    assert isinstance(mem1.data["b"], SyncedDict)
    mem1.data["b"].update({"d": 3})
    assert mem1.data == {"a": 1, "b": {"c": 2, "d": 3}}

    mem2 = Memory()
    assert isinstance(mem2.data["b"], SyncedDict)
    assert mem2.data == {"a": 1, "b": {"c": 2, "d": 3}}


def test_set_and_get_as_list(Memory):
    """Test setting and getting a list value in Memory."""
    mem = Memory()
    expected = [1, 2, 3]
    mem.items = expected
    assert isinstance(mem.items, SyncedList)
    assert isinstance(mem.items.aslist(), list)

    new_list = mem.items.aslist()
    assert new_list == expected

    copied_list = deepcopy(new_list)
    assert copied_list == expected


def test_set_and_get_as_dict(Memory):
    """Test setting and getting a dict value in Memory."""
    mem = Memory()
    expected = {"theme": "dark", "volume": 0.75}
    mem.settings = expected
    assert isinstance(mem.settings, SyncedDict)
    assert isinstance(mem.settings.asdict(), dict)

    new_dict = mem.settings.asdict()
    assert new_dict == expected

    copied_dict = deepcopy(new_dict)
    assert copied_dict == expected


def test_aslist_returns_independent_copy(Memory):
    """Test that .aslist() returns an independent copy."""
    mem = Memory()
    mem.items = [1, 2, 3]

    copy1 = mem.items.aslist()
    copy1.append(4)

    assert mem.items.aslist() == [1, 2, 3]
    assert copy1 == [1, 2, 3, 4]


def test_asdict_returns_independent_copy(Memory):
    """Test that .asdict() returns an independent copy."""
    mem = Memory()
    mem.settings = {"theme": "dark"}

    copy1 = mem.settings.asdict()
    copy1["theme"] = "light"

    assert mem.settings.asdict() == {"theme": "dark"}
    assert copy1 == {"theme": "light"}


def test_pickle_aslist_to_file(Memory):
    """Test that .aslist() result can be pickled to a file."""
    mem = Memory()
    mem.items = [{"role": "user", "content": "hello"}]

    plain_list = mem.items.aslist()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
        temp_path = Path(f.name)
        pickle.dump(plain_list, f)

    try:
        with open(temp_path, "rb") as f:
            loaded = pickle.load(f)
        assert loaded == [{"role": "user", "content": "hello"}]
    finally:
        temp_path.unlink()


def test_pickle_asdict_to_file(Memory):
    """Test that .asdict() result can be pickled to a file."""
    mem = Memory()
    mem.config = {"api_key": "secret", "timeout": 30}

    plain_dict = mem.config.asdict()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
        temp_path = Path(f.name)
        pickle.dump(plain_dict, f)

    try:
        with open(temp_path, "rb") as f:
            loaded = pickle.load(f)
        assert loaded == {"api_key": "secret", "timeout": 30}
    finally:
        temp_path.unlink()


def test_synced_list_mutations_persist(Memory):
    """Test that mutations to SyncedList actually persist."""
    mem = Memory()
    mem.items = [1, 2, 3]

    mem.items.append(4)
    mem.items.extend([5, 6])

    assert mem.items.aslist() == [1, 2, 3, 4, 5, 6]


def test_synced_dict_mutations_persist(Memory):
    """Test that mutations to SyncedDict actually persist."""
    mem = Memory()
    mem.config = {"a": 1}

    mem.config["b"] = 2
    mem.config.update({"c": 3})

    assert mem.config.asdict() == {"a": 1, "b": 2, "c": 3}


def test_nested_list_of_dicts(Memory):
    """Test list containing dicts can be safely copied."""
    mem = Memory()
    mem.messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]

    plain = mem.messages.aslist()
    pickled = pickle.dumps(plain)
    unpickled = pickle.loads(pickled)

    assert unpickled == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_cannot_pickle_synced_objects_directly(Memory):
    """Test that SyncedList/SyncedDict can't be pickled (have thread locks)."""
    mem = Memory()
    mem.items = [1, 2, 3]

    with pytest.raises((TypeError, pickle.PicklingError)):
        pickle.dumps(mem.items)

    assert pickle.dumps(mem.items.aslist())


def test_external_library_deepcopy_compatibility(Memory):
    """Simulate external library (like LiteLLM) doing deepcopy."""
    mem = Memory()
    mem.messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
    ]

    messages = mem.messages.aslist()
    copied = deepcopy(messages)

    assert copied == messages
    assert copied is not messages
