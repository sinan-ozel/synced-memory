# Basic Usage

## Creating a Memory Instance

```python
from synced_memory.redis import Memory      # Redis
from synced_memory.dragonflydb import Memory  # DragonflyDB

mem = Memory()
```

By default, `Memory` connects to `redis:6379` (or `dragonflydb:6379` for the DragonflyDB
backend) and uses the prefix `memory:`.

## Setting Values

```python
mem.counter = 42
mem.name = "Alice"
mem.active = True
mem.score = 98.5
mem.items = [1, 2, 3]
mem.config = {"theme": "dark", "lang": "en"}
```

All values are JSON-serialized and written to the backend.

## Getting Values

```python
print(mem.counter)  # 42
print(mem.name)     # Alice
print(mem.active)   # True
print(mem.items)    # [1, 2, 3]
```

## Checking if Attributes Exist

```python
if hasattr(mem, 'counter'):
    print(f"Counter exists: {mem.counter}")

try:
    value = mem.nonexistent
except AttributeError:
    print("Attribute doesn't exist")
```

## Deleting Values

```python
mem.temp = "temporary"
del mem.temp
# Now mem.temp raises AttributeError
```

## Working with Complex Data

```python
mem.user = {
    "name": "Alice",
    "profile": {
        "age": 30,
        "preferences": {
            "theme": "dark",
            "notifications": ["email", "push"]
        }
    }
}

print(mem.user["profile"]["age"])  # 30
```

## Persistence

Values persist across program restarts:

```python
# Run 1
mem = Memory()
mem.persistent_value = "I will survive!"

# Later, after program restart
mem = Memory()
print(mem.persistent_value)  # "I will survive!"
```

## Multiprocessing Safety

```python
from multiprocessing import Process
from synced_memory.redis import Memory      # Redis
from synced_memory.dragonflydb import Memory  # DragonflyDB

def worker(worker_id):
    mem = Memory()
    print(f"Worker {worker_id} sees: {mem.shared_value}")

mem = Memory()
mem.shared_value = "hello"

processes = [Process(target=worker, args=(i,)) for i in range(5)]
for p in processes:
    p.start()
for p in processes:
    p.join()
```

## Redis Connection Resilience

If the backend is temporarily unavailable, changes are queued locally and
flushed automatically when the connection is restored:

```python
mem = Memory()
mem.offline_value = "queued"  # Queued locally if backend is down
# When backend comes back online, the change is synced automatically
```
