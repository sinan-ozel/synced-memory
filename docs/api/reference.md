# API Reference

## Base Classes

### MemoryBase

::: synced_memory.common.MemoryBase
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### PrefixedMemoryBase

::: synced_memory.common.PrefixedMemoryBase
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

## Redis Backend

### Memory

::: synced_memory.redis.Memory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### PrefixedMemory

::: synced_memory.redis.PrefixedMemory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

## DragonflyDB Backend

### Memory

::: synced_memory.dragonflydb.Memory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### PrefixedMemory

::: synced_memory.dragonflydb.PrefixedMemory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

## Helpers

### SyncedList

::: synced_memory.common.SyncedList
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### SyncedDict

::: synced_memory.common.SyncedDict
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Backend hostname |
| `REDIS_PORT` | `6379` | Backend port |
| `REDIS_PREFIX` | `memory:` | Key prefix for namespacing |

## Exceptions

synced-memory uses standard Python exceptions:

- `AttributeError`: Raised when accessing non-existent attributes
- `TypeError`: Raised when assigning a non-JSON-serializable value
- `redis.ConnectionError`: Raised when the backend connection fails (if not caught by the circuit breaker)
