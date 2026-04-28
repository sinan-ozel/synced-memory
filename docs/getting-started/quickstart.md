# Quickstart

This guide will get you up and running with synced-memory in minutes.

## Choose a Backend

Import from the backend you want to use:

```python
from synced_memory.redis import Memory      # Redis
from synced_memory.dragonflydb import Memory  # DragonflyDB
```

Both backends expose the same API.

## Basic Usage

```python
from synced_memory.redis import Memory

mem = Memory()
mem.counter = 0
mem.username = "alice"
mem.settings = {"theme": "dark", "notifications": True}

print(mem.counter)    # 0
print(mem.username)   # alice
print(mem.settings)   # {'theme': 'dark', 'notifications': True}
```

## Cross-Process Sharing

```python
# Process 1
from synced_memory.redis import Memory

mem = Memory()
mem.shared_value = "Hello from Process 1"
```

```python
# Process 2 (different Python process)
from synced_memory.redis import Memory

mem = Memory()
print(mem.shared_value)  # "Hello from Process 1"
```

## Context Manager

```python
with Memory() as memory:
    memory.session = "active"
    print(memory.session)  # "active"

# Later, in another process:
with Memory() as memory:
    print(memory.session)  # "active"
```

## Auto-Syncing Collections

Lists and dictionaries automatically sync to the backend:

```python
mem = Memory()

mem.tasks = ["task1", "task2"]
mem.tasks.append("task3")  # Automatically syncs

mem.config = {"lang": "en"}
mem.config["theme"] = "dark"  # Automatically syncs

mem.data = {"user": {"name": "Alice", "age": 30}}
mem.data["user"]["age"] = 31  # Syncs the entire structure
```

## Converting to Plain Types

When you need regular Python objects (for serialization, pickling, etc.):

```python
mem.items = [1, 2, 3]
plain_list = mem.items.aslist()  # Returns: [1, 2, 3]

mem.config = {"key": "value"}
plain_dict = mem.config.asdict()  # Returns: {'key': 'value'}

import pickle
pickle.dump(plain_list, open('data.pkl', 'wb'))
```

## Next Steps

- Learn about [basic usage patterns](../guide/basic-usage.md)
- Explore [auto-synced collections](../guide/collections.md)
- Set up [namespacing](../guide/namespacing.md) for multi-tenant apps
- Use [agent memory](../guide/agents.md) for conversational AI
