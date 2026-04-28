import os
from copy import deepcopy
import json
import time
import pickle
import tempfile
from pathlib import Path

import pytest
import redis

from synced_memory.redis import Memory, SyncedDict, SyncedList


@pytest.fixture(scope="function", autouse=True)
def setup_env_and_clear_redis():
    os.environ["REDIS_HOST"] = "redis"
    os.environ["REDIS_PORT"] = "6379"
    mem = Memory()
    client = mem._connect()
    if client:
        keys = client.keys(f"{mem._prefix}*")
        if keys:
            client.delete(*keys)
    yield
    # Cleanup after each test
    mem = Memory()
    client = mem._connect()
    if client:
        keys = client.keys(f"{mem._prefix}*")
        if keys:
            client.delete(*keys)


def get_redis_value(key: str, prefix="memory:", host="redis", port=6379):
    client = redis.Redis(host=host, port=port)
    raw = client.get(f"{prefix}{key}")
    if raw is not None:
        return json.loads(raw)
    return None


def get_redis_value_obj(key: str, prefix="memory:", host="redis", port=6379):
    client = redis.Redis(host=host, port=port)
    raw = client.get(f"{prefix}{key}")
    if raw is not None:
        return json.loads(raw)
    return None


def test_set_and_get_scalar():
    """Test setting and getting a scalar value across Memory instances."""
    mem1 = Memory()
    mem2 = Memory()
    mem1.answer = 42
    assert mem2.answer == 42
    obj = get_redis_value_obj("answer")
    assert obj["value"] == 42
    assert isinstance(obj["last_modified"], int)
    assert mem1._last_modified["answer"] == obj["last_modified"]


def test_set_and_get_dict():
    """Test setting and getting a dictionary value in Memory."""
    mem = Memory()
    expected = {"theme": "dark", "volume": 0.75}
    mem.settings = expected
    assert mem.settings == expected
    obj = get_redis_value_obj("settings")
    assert obj["value"] == expected
    assert isinstance(obj["last_modified"], int)
    assert mem._last_modified["settings"] == obj["last_modified"]


def test_set_and_get_list():
    """Test setting and getting a list value in Memory."""
    mem = Memory()
    expected = [1, 2, 3]
    mem.items = expected
    assert mem.items == expected
    obj = get_redis_value_obj("items")
    assert obj["value"] == expected
    assert isinstance(obj["last_modified"], int)
    assert mem._last_modified["items"] == obj["last_modified"]


def test_overwrite_existing_key():
    """Test that assigning a new value overwrites the existing Redis key."""
    mem = Memory()
    mem.key = "initial"
    obj1 = get_redis_value_obj("key")
    assert obj1["value"] == "initial"
    mem.key = "updated"
    assert mem.key == "updated"
    obj2 = get_redis_value_obj("key")
    assert obj2["value"] == "updated"
    assert obj2["last_modified"] >= obj1["last_modified"]


def test_missing_attribute_raises():
    """Test that accessing an unset attribute raises AttributeError."""
    mem = Memory()
    with pytest.raises(AttributeError):
        _ = mem.does_not_exist


def test_internal_attributes_not_stored():
    """Test that internal attributes are not stored in Redis."""
    mem = Memory()
    assert hasattr(mem, "_host")
    assert "_host" not in mem.__dict__.get("_attributes", {})


def test_multiple_instances_consistency():
    """Test that Memory instances share a consistent state."""
    m1 = Memory()
    m2 = Memory()
    m1.shared = {"a": 10}
    assert m2.shared == {"a": 10}
    obj = get_redis_value_obj("shared")
    assert obj["value"] == {"a": 10}
    assert isinstance(obj["last_modified"], int)


def test_attribute_persistence_across_instances():
    """Test that attributes persist across new Memory instances."""
    Memory().temp = "hello"
    mem = Memory()
    assert mem.temp == "hello"
    obj = get_redis_value_obj("temp")
    assert obj["value"] == "hello"
    assert isinstance(obj["last_modified"], int)


def test_set_is_non_blocking_when_redis_unavailable(monkeypatch):
    """Test that writes do not block repeatedly when Redis is unavailable.

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

    # 10 writes should complete well under the single timeout (0.5s),
    # proving the circuit breaker prevents repeated blocking
    assert elapsed < mem._timeout, (
        f"10 writes took {elapsed:.3f}s — expected < {mem._timeout}s. "
        "Writes are still blocking on connection timeout."
    )
    assert all(mem._attributes.get(f"key_{i}") == i for i in range(10))
    assert len(mem._queue) >= 10


def test_queue_flush_when_redis_restored(monkeypatch):
    """Test queueing when Redis is down and flushing when it's restored."""
    # Simulate bad Redis environment (Redis is down)
    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")

    mem = Memory()
    mem.foo = "bar"

    # Confirm value is queued
    assert mem._queue[-1][0] == "foo"
    assert mem._queue[-1][1]["value"] == "bar"
    assert mem.foo == "bar"

    # Simulate Redis restored
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")

    mem_restored = Memory(redis_prefix=mem._prefix)
    mem_restored._queue = mem._queue.copy()
    mem_restored._flush_queue()

    obj = get_redis_value_obj("foo")
    assert obj["value"] == "bar"
    assert isinstance(obj["last_modified"], int)


def test_queue_overwrite_before_redis_restored(monkeypatch):
    """Test that latest queued value is saved after Redis is restored."""
    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")

    mem = Memory()
    mem.config = {"a": 1}
    mem.config = {"a": 2}

    assert mem.config == {"a": 2}
    assert mem._queue[-1][0] == "config"
    assert mem._queue[-1][1]["value"] == {"a": 2}

    # Redis comes back online
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")

    mem_restored = Memory(redis_prefix=mem._prefix)
    mem_restored._queue = mem._queue.copy()
    mem_restored._flush_queue()

    obj = get_redis_value_obj("config")
    assert obj["value"] == {"a": 2}
    assert isinstance(obj["last_modified"], int)


@pytest.mark.depends(on=["test_set_and_get_scalar"])
def test_memory_with_custom_prefix():
    """Test that Memory with a custom prefix stores and retrieves data
    correctly."""
    custom_prefix = "custom:"
    mem = Memory(redis_prefix=custom_prefix)
    mem.status = "active"
    assert mem.status == "active"

    # Verify it's not saved under default prefix
    assert get_redis_value("status", prefix="memory:") is None

    # Verify it's saved under the custom prefix
    obj = get_redis_value_obj("status", prefix=custom_prefix)
    assert obj["value"] == "active"
    assert isinstance(obj["last_modified"], int)


def test_set_and_delete_attribute(monkeypatch):
    mem = Memory()
    mem.key = "value"

    # Delete attribute, should queue deletion since Redis unavailable
    del mem.key

    # Check attribute removed locally
    with pytest.raises(AttributeError):
        _ = mem.key


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_delete_attribute_queues_if_redis_down(monkeypatch):
    """Test that deleting an attribute while Redis is down queues the deletion
    properly."""
    # First, ensure Redis is up to set the value
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")
    mem = Memory()
    mem.queued_key = "queued value"

    # Now simulate Redis going down
    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")
    mem_down = Memory(redis_prefix=mem._prefix)
    mem_down._attributes = mem._attributes.copy()  # simulate state carry-over

    # Delete attribute, should queue deletion
    del mem_down.queued_key

    # Should raise since it's removed from local cache
    with pytest.raises(AttributeError):
        _ = mem_down.queued_key

    # Check deletion was queued (None marks deletion)
    assert any(
        q[0] == "queued_key" and q[1]["value"] is None for q in mem_down._queue
    )


@pytest.mark.depends(
    on=[
        "test_set_and_delete_attribute",
        "test_queue_flush_when_redis_restored",
        "test_queue_overwrite_before_redis_restored",
    ]
)
def test_background_flush_automatically(monkeypatch):
    """Test that the background flush loop automatically flushes queued data
    when Redis comes back online."""
    # Simulate Redis being down
    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")
    mem = Memory()

    # Set attribute (should be queued)
    mem.test_key = "queued_value"

    assert mem._attributes.get("test_key") == "queued_value"
    assert mem._queue[-1][0] == "test_key"
    assert mem._queue[-1][1]["value"] == "queued_value"
    assert mem.test_key == "queued_value"

    # Redis comes back online
    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")

    mem_restored = Memory(redis_prefix=mem._prefix)
    mem_restored._queue = mem._queue.copy()

    # Wait for background thread to pick up the connection and flush
    time.sleep(2)

    obj = get_redis_value_obj("test_key")
    assert obj["value"] == "queued_value"
    assert isinstance(obj["last_modified"], int)

    # Clean up
    del mem.test_key


def test_memory_loads_existing_keys_on_init():
    """Test that Memory instance loads existing Redis keys on
    initialization."""
    # Set a key using one instance
    mem1 = Memory()
    mem1.user = {"name": "Alice", "role": "admin"}

    # Simulate new process / restart by creating a fresh instance
    mem2 = Memory()

    # Should have preloaded the same key from Redis
    assert "user" in mem2._attributes
    assert mem2.user == {"name": "Alice", "role": "admin"}
    assert isinstance(mem2._last_modified["user"], int)


def test_basic_context_set_and_get():
    """Test that values set in a `with Memory()` context are correctly
    persisted and can be retrieved in a later context block."""
    with Memory() as memory:
        memory.test_key = "hello world"

    with Memory() as memory:
        assert memory.test_key == "hello world"
        assert isinstance(memory._last_modified["test_key"], int)


def test_context_lifecycle_and_del():
    """Test that Memory context persists values even after the object is
    deleted, as long as Redis remains available."""
    with Memory() as memory:
        memory.context = "Je me souviens."

    # Delete outside the context
    del memory

    # Reload and check persistence
    with Memory() as memory:
        assert memory.context == "Je me souviens."
        assert isinstance(memory._last_modified["context"], int)


def test_non_serializable_value():
    """Test that assigning a non-serializable value (e.g., a lambda function)
    to a Memory attribute raises a PicklingError."""
    with pytest.raises(TypeError):
        with Memory() as memory:
            memory.bad = lambda x: x * 2  # Not serializable


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_works_if_redis_never_comes_alive(monkeypatch):
    """Test that deleting an attribute while Redis is down queues the deletion
    properly."""
    monkeypatch.setenv("REDIS_HOST", "nonexistent-host")
    monkeypatch.setenv("REDIS_PORT", "9999")
    with Memory() as memory:
        memory.test_key = "hello world"
        assert memory.test_key == "hello world"
        del memory.test_key
        with pytest.raises(AttributeError):
            _ = memory.queued_key

    monkeypatch.setenv("REDIS_HOST", "redis")
    monkeypatch.setenv("REDIS_PORT", "6379")


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_append_to_list():
    """Test that appending to a list attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.numbers = [1, 2]
    assert type(mem1.numbers) == SyncedList
    mem1.numbers.append(3)

    mem2 = Memory()
    assert mem2.numbers == [1, 2, 3]


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_insert_to_list():
    """Test that inserting to a list attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.numbers = [1, 2, 4]
    assert type(mem1.numbers) == SyncedList
    mem1.numbers.insert(2, 3)

    mem2 = Memory()
    assert mem2.numbers == [1, 2, 3, 4]


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_extend_list():
    """Test that extending a list attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.numbers = [1, 2]
    mem1.numbers.extend([3, 4])

    mem2 = Memory()
    assert mem2.numbers == [1, 2, 3, 4]


@pytest.mark.depends(on=["test_set_and_delete_attribute"])
def test_update_dict():
    """Test that updating a dict attribute persists across Memory instances."""
    mem1 = Memory()
    mem1.data = {"a": 1}
    assert type(mem1.data) == SyncedDict
    mem1.data.update({"b": 2})

    mem2 = Memory()
    assert mem2.data == {"a": 1, "b": 2}


@pytest.mark.depends(on=["test_update_dict"])
def test_update_dict_in_context():
    """Test that updating a dict attribute persists across Memory instances."""
    with Memory() as memory:
        memory.data = {"a": 1}
        memory.data.update({"b": 2})

    del memory

    with Memory() as memory:
        assert memory.data == {"a": 1, "b": 2}


@pytest.mark.depends(on=["test_append_to_list"])
def test_append_to_a_nested_list():
    """Test that appending to a list attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.list_of_lists_of_numbers = [[1, 2], [3, 4]]
    assert type(mem1.list_of_lists_of_numbers) == SyncedList
    assert type(mem1.list_of_lists_of_numbers[1]) == SyncedList
    mem1.list_of_lists_of_numbers[1].append(5)

    mem2 = Memory()
    assert mem2.list_of_lists_of_numbers == [[1, 2], [3, 4, 5]]


@pytest.mark.depends(on=["test_update_dict"])
def test_update_nested_dict():
    """Test that updating a nested dict attribute persists across Memory
    instances."""
    mem1 = Memory()
    mem1.data = {"a": 1, "b": {"c": 2}}
    assert type(mem1.data["b"]) == SyncedDict
    mem1.data["b"].update({"d": 3})
    assert mem1.data == {"a": 1, "b": {"c": 2, "d": 3}}

    mem2 = Memory()
    assert type(mem2.data["b"]) == SyncedDict
    assert mem2.data == {"a": 1, "b": {"c": 2, "d": 3}}


def test_set_and_get_as_list():
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


def test_set_and_get_as_dict():
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


def test_aslist_returns_independent_copy():
    """Test that .aslist() returns an independent copy."""
    mem = Memory()
    mem.items = [1, 2, 3]

    # Get a copy
    copy1 = mem.items.aslist()

    # Modify the copy
    copy1.append(4)

    # Original should be unchanged
    assert mem.items.aslist() == [1, 2, 3]
    assert copy1 == [1, 2, 3, 4]


def test_asdict_returns_independent_copy():
    """Test that .asdict() returns an independent copy."""
    mem = Memory()
    mem.settings = {"theme": "dark"}

    # Get a copy
    copy1 = mem.settings.asdict()

    # Modify the copy
    copy1["theme"] = "light"

    # Original should be unchanged
    assert mem.settings.asdict() == {"theme": "dark"}
    assert copy1 == {"theme": "light"}


def test_pickle_aslist_to_file():
    """Test that .aslist() result can be pickled to a file."""
    mem = Memory()
    mem.items = [{"role": "user", "content": "hello"}]

    plain_list = mem.items.aslist()

    # Pickle to file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
        temp_path = Path(f.name)
        pickle.dump(plain_list, f)

    try:
        # Unpickle from file
        with open(temp_path, "rb") as f:
            loaded = pickle.load(f)

        assert loaded == [{"role": "user", "content": "hello"}]
    finally:
        temp_path.unlink()


def test_pickle_asdict_to_file():
    """Test that .asdict() result can be pickled to a file."""
    mem = Memory()
    mem.config = {"api_key": "secret", "timeout": 30}

    plain_dict = mem.config.asdict()

    # Pickle to file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
        temp_path = Path(f.name)
        pickle.dump(plain_dict, f)

    try:
        # Unpickle from file
        with open(temp_path, "rb") as f:
            loaded = pickle.load(f)

        assert loaded == {"api_key": "secret", "timeout": 30}
    finally:
        temp_path.unlink()


def test_synced_list_mutations_persist():
    """Test that mutations to SyncedList actually persist."""
    mem = Memory()
    mem.items = [1, 2, 3]

    # Mutate via proxy
    mem.items.append(4)
    mem.items.extend([5, 6])

    # Verify persisted
    assert mem.items.aslist() == [1, 2, 3, 4, 5, 6]


def test_synced_dict_mutations_persist():
    """Test that mutations to SyncedDict actually persist."""
    mem = Memory()
    mem.config = {"a": 1}

    # Mutate via proxy
    mem.config["b"] = 2
    mem.config.update({"c": 3})

    # Verify persisted
    assert mem.config.asdict() == {"a": 1, "b": 2, "c": 3}


def test_nested_list_of_dicts():
    """Test list containing dicts can be safely copied."""
    mem = Memory()
    mem.messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]

    # Get as plain list
    plain = mem.messages.aslist()

    # Should be picklable
    pickled = pickle.dumps(plain)
    unpickled = pickle.loads(pickled)

    assert unpickled == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_cannot_pickle_synced_objects_directly():
    """Test that SyncedList/SyncedDict can't be pickled (have thread locks)."""
    mem = Memory()
    mem.items = [1, 2, 3]

    # This should fail (has thread locks)
    with pytest.raises((TypeError, pickle.PicklingError)):
        pickle.dumps(mem.items)

    # But .aslist() works
    assert pickle.dumps(mem.items.aslist())  # No error


def test_external_library_deepcopy_compatibility():
    """Simulate external library (like LiteLLM) doing deepcopy."""
    mem = Memory()
    mem.messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
    ]

    # External library gets the data
    messages = mem.messages.aslist()

    # External library does deepcopy (like LiteLLM logging)
    copied = deepcopy(messages)

    # Should work without errors
    assert copied == messages
    assert copied is not messages  # Actually copied
