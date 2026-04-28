![Tests & Lint](https://github.com/sinan-ozel/synced-memory/actions/workflows/ci.yaml/badge.svg?branch=main)
![PyPI](https://img.shields.io/pypi/v/synced-memory.svg)
![Downloads](https://static.pepy.tech/badge/synced-memory)
![Monthly Downloads](https://static.pepy.tech/badge/synced-memory/month)
![License](https://img.shields.io/github/license/sinan-ozel/synced-memory.svg)
[![Documentation](https://img.shields.io/badge/docs-github--pages-blue)](https://sinan-ozel.github.io/synced-memory/)


# 🗄️ synced-memory

A production-ready Python class for seamless, multiprocessing-safe, persistent key-value storage
using Redis or DragonflyDB as a backend. If the backend is unavailable, values are cached locally
and queued for syncing when it comes back online. All values are serialized as JSON, and you
interact with it using natural Python attribute access.

# Purpose

The intention is to use this with agentic workflows deployed as microservices,
allowing for multiple instances of the same pod to share their state.


## ✨ Features

- 🔄 **Multiprocessing-safe**: All processes share the same state via Redis or DragonflyDB.
- 🧠 **Pythonic API**: Set and get attributes as if they were regular object properties.
- 🕰️ **Persistence**: Values survive process restarts and context blocks.
- 🚦 **Resilient**: If the backend is down, changes are queued and flushed when it returns.
- 🧩 **Customizable**: Prefixes and conversation IDs for namespacing.
- 🧵 **Background sync**: Queued changes are flushed automatically in the background.

## 🚀 Quickstart

```bash
pip install synced-memory
```

```python
from synced_memory.redis import Memory

mem = Memory()
mem.answer = 42
print(mem.answer)  # 42

# Across processes or instances:
mem2 = Memory()
print(mem2.answer)  # 42

mem.settings = {"theme": "dark", "volume": 0.75}
print(mem.settings)  # {'theme': 'dark', 'volume': 0.75}
```

To use DragonflyDB instead:

```python
from synced_memory.dragonflydb import Memory

mem = Memory()
mem.answer = 42
```

## 🧑‍💻 Context Management

You can use `Memory` as a context manager for automatic resource handling:

```python
with Memory() as memory:
    memory.session = "active"
    print(memory.session)  # "active"

# Later, in a new context:
with Memory() as memory:
    print(memory.session)  # "active"
```

## 🔄 Auto-Synced Collections

Lists and dictionaries are automatically wrapped as `SyncedList` and `SyncedDict`, which sync changes to the backend immediately:

```python
mem = Memory()
mem.items = [1, 2, 3]
mem.items.append(4)  # Automatically syncs

mem2 = Memory()
print(mem2.items)  # [1, 2, 3, 4]

mem.config = {"theme": "dark"}
mem.config["lang"] = "en"  # Automatically syncs
print(mem2.config)  # {'theme': 'dark', 'lang': 'en'}
```

**Nested structures** work too:
```python
mem.data = {"user": {"preferences": {"color": "blue"}}}
mem.data["user"]["preferences"]["color"] = "red"  # Syncs!
```

### Converting to Plain Python Types

For libraries that need plain Python objects (serialization, pickling, etc.):

```python
mem.items = [1, 2, 3]
plain_list = mem.items.aslist()  # Returns regular list

mem.config = {"key": "value"}
plain_dict = mem.config.asdict()  # Returns regular dict

import pickle
pickle.dump(plain_list, file)  # Works!
```

## 🗂️ Namespacing

By default, `synced-memory` uses `memory:` as its key prefix. Override with `REDIS_PREFIX`:

```python
mem = Memory()
mem.state = {"step": 1}
print(mem.state)  # {'step': 1}
```

## Agents

Use `ConversationMemory` to namespace memory by conversation ID:

```python
from synced_memory.redis import ConversationMemory

conversation_id = uuid()
mem = ConversationMemory(conversation_id=conversation_id)
mem.messages = messages
```

## ⚙️ Environment Variables

- `REDIS_HOST`: Backend hostname (default: `redis`)
- `REDIS_PORT`: Backend port (default: `6379`)
- `REDIS_PREFIX`: Key prefix (default: `memory:`)

```

--- WHEN UPDATING README.md: YOU CAN KEEP EVERYTHING BELOW THIS LINE ---
```

# 🛠️ Development

The only requirement is 🐳 Docker.
(The `.devcontainer` and `tasks.json` are prepared assuming a *nix system, but if you know the commands, this will work on Windows, too.)

1. Clone the repo.
2. Branch out.
3. Open in "devcontainer" on VS Code and start developing. Run `pytest` under `tests` to test.
4. Alternatively, if you are a fan of Test-Driven Development like me, you can run the tests without getting on a container. `.vscode/tasks.json` has the command to do so, but it's also listed here:
```
docker compose -f tests/docker-compose.yaml up --build --abort-on-container-exit --exit-code-from test
```
