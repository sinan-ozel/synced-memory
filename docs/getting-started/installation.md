# Installation

## Requirements

- Python 3.10+
- Redis 7+ or DragonflyDB (local or remote)
- Docker (optional, for development)

## Install from PyPI

```bash
pip install synced-memory
```

## Install from Source

```bash
git clone https://github.com/sinan-ozel/synced-memory.git
cd synced-memory
pip install .
```

## Backend Setup

synced-memory requires a Redis-compatible server. You can use Redis or DragonflyDB.

### Option 1: Use Docker (Recommended)

**Redis:**
```bash
docker run -d -p 6379:6379 redis:7
```

**DragonflyDB:**
```bash
docker run -d -p 6379:6379 docker.dragonflydb.io/dragonflydb/dragonfly
```

### Option 2: Install Redis Locally

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install redis-server
sudo systemctl start redis-server
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `REDIS_HOST` | `redis` | Backend hostname |
| `REDIS_PORT` | `6379` | Backend port |
| `REDIS_PREFIX` | `memory:` | Key prefix for namespacing |

Example `.env` file:

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PREFIX=myapp:
```

## Verify Installation

```python
from synced_memory.redis import Memory

mem = Memory()
mem.test = "Hello, synced-memory!"
print(mem.test)  # Hello, synced-memory!
```
