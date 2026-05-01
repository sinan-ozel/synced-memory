# Auto-Synced Collections

synced-memory automatically wraps lists and dictionaries in `SyncedList` and `SyncedDict`.
Supported mutations on these wrappers are immediately written back to the backend.

## Auto-Synced Lists (`SyncedList`)

### Supported Operations

The following operations sync automatically:

| Operation | Example |
|-----------|---------|
| `append(item)` | `mem.tasks.append("new")` |
| `extend(iterable)` | `mem.tasks.extend(["a", "b"])` |
| `insert(index, item)` | `mem.tasks.insert(0, "first")` |
| `remove(item)` | `mem.tasks.remove("done")` |
| `pop([index])` | `mem.tasks.pop()` |

```python
from synced_memory.redis import Memory      # Redis
from synced_memory.dragonflydb import Memory  # DragonflyDB

mem = Memory()
mem.tasks = [1, 2, 3]

mem.tasks.append(4)       # [1, 2, 3, 4]
mem.tasks.extend([5, 6])  # [1, 2, 3, 4, 5, 6]
mem.tasks.insert(0, 0)    # [0, 1, 2, 3, 4, 5, 6]
mem.tasks.remove(0)       # [1, 2, 3, 4, 5, 6]
mem.tasks.pop()           # [1, 2, 3, 4, 5]

mem2 = Memory()
print(mem2.tasks)  # [1, 2, 3, 4, 5]
```

!!! warning "Unsupported in-place operations"
    Operations not listed above (e.g. `sort`, `reverse`, index assignment
    `mem.items[0] = x`) are inherited from `list` but **do not sync**. Re-assign the whole
    attribute after such operations:

    ```python
    # Does NOT sync:
    mem.items.pop()

    # Use this instead:
    plain = mem.items.aslist()
    plain.pop()
    mem.items = plain  # syncs
    ```

## Auto-Synced Dictionaries (`SyncedDict`)

### Supported Operations

| Operation | Example |
|-----------|---------|
| `__setitem__(key, value)` | `mem.config["key"] = "val"` |
| `update(other)` | `mem.config.update({"a": 1})` |
| `pop(key[, default])` | `mem.config.pop("key")` |

```python
mem = Memory()
mem.config = {"theme": "dark", "lang": "en"}

mem.config["notifications"] = True
mem.config.update({"font": "Arial", "size": 12})

mem2 = Memory()
print(mem2.config)
# {'theme': 'dark', 'lang': 'en', 'notifications': True, 'font': 'Arial', 'size': 12}
```

!!! warning "Unsupported in-place operations"
    `pop`, `popitem`, `clear`, `setdefault`, and `del mem.config["key"]` are inherited
    from `dict` but **do not sync**. Re-assign the whole attribute after such operations.

## Nested Collections

synced-memory handles deeply nested structures — any mutation at any level syncs
the top-level attribute:

```python
mem = Memory()
mem.data = {"users": [{"name": "Alice", "scores": [95, 87]}]}

mem.data["users"][0]["scores"].append(92)  # syncs

mem2 = Memory()
print(mem2.data["users"][0]["scores"])  # [95, 87, 92]
```

## Converting to Plain Python Types

Use `.aslist()` and `.asdict()` when you need regular Python objects:

```python
mem.items = [1, 2, 3]
plain_list = mem.items.aslist()  # plain list, recursively converted

mem.config = {"key": "value", "nested": {"a": 1}}
plain_dict = mem.config.asdict()  # plain dict, recursively converted

import pickle
pickle.dump(plain_list, open('data.pkl', 'wb'))  # works
```

Both methods convert nested `SyncedList`/`SyncedDict` objects recursively.

## Type Checking

```python
from synced_memory.redis import Memory
from synced_memory.common import SyncedList, SyncedDict

mem = Memory()
mem.items = [1, 2, 3]
mem.config = {"key": "value"}

isinstance(mem.items, SyncedList)   # True
isinstance(mem.config, SyncedDict)  # True

plain = mem.items.aslist()
isinstance(plain, list)        # True
isinstance(plain, SyncedList)  # False
```
