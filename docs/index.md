# 🗄️ synced-memory

![Tests & Lint](https://github.com/sinan-ozel/synced-memory/actions/workflows/ci.yaml/badge.svg?branch=main)
![PyPI](https://img.shields.io/pypi/v/synced-memory.svg)
![Downloads](https://static.pepy.tech/badge/synced-memory)
![Monthly Downloads](https://static.pepy.tech/badge/synced-memory/month)
![License](https://img.shields.io/github/license/sinan-ozel/synced-memory.svg)

A production-ready Python class for seamless, multiprocessing-safe, persistent key-value storage
using Redis or DragonflyDB as a backend. If the backend is unavailable, values are cached locally
and queued for syncing when it comes back online. All values are serialized as JSON, and you
interact with it using natural Python attribute access.

## Purpose

The intention is to use this with agentic workflows deployed as microservices,
allowing for multiple instances of the same pod to share their state.

## ✨ Features

- 🔄 **Multiprocessing-safe**: All processes share the same state via Redis or DragonflyDB.
- 🧠 **Pythonic API**: Set and get attributes as if they were regular object properties.
- 🕰️ **Persistence**: Values survive process restarts and context blocks.
- 🚦 **Resilient**: If the backend is down, changes are queued and flushed when it returns.
- 🧩 **Customizable**: Prefixes and conversation IDs for namespacing.
- 🧵 **Background sync**: Queued changes are flushed automatically in the background.

## Quick Example

```python
from synced_memory.redis import Memory      # Redis
from synced_memory.dragonflydb import Memory  # DragonflyDB

mem = Memory()
mem.answer = 42
print(mem.answer)  # 42

# Across processes or instances:
mem2 = Memory()
print(mem2.answer)  # 42

mem.settings = {"theme": "dark", "volume": 0.75}
print(mem.settings)  # {'theme': 'dark', 'volume': 0.75}
```

## Getting Started

Check out the [Installation Guide](getting-started/installation.md) and [Quickstart Tutorial](getting-started/quickstart.md) to get up and running.

## License

MIT
