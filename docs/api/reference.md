# API Reference

## Classes

### Memory

::: synced_memory.redis.Memory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### ConversationMemory

::: synced_memory.redis.ConversationMemory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### SyncedList

::: synced_memory.redis.SyncedList
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### SyncedDict

::: synced_memory.redis.SyncedDict
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
