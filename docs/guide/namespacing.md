# Namespacing

synced-memory supports namespacing through key prefixes, allowing multiple applications
or tenants to share the same backend without key collisions.

## Default Prefix

By default the prefix is `memory:`:

```python
from synced_memory.redis import Memory      # Redis
from synced_memory.dragonflydb import Memory  # DragonflyDB

mem = Memory()
mem.counter = 1
# Stored in backend as: memory:counter
```

## Custom Prefix via Environment Variable

```bash
export REDIS_PREFIX="myapp:"
```

```python
mem = Memory()
mem.counter = 1
# Stored as: myapp:counter
```

## Custom Prefix via Constructor

Pass `db_prefix` directly:

```python
mem = Memory(db_prefix="session_123:")
mem.value = "hello"
# Stored as: session_123:value
```

## Multi-Tenant Applications

```python
from synced_memory.redis import Memory      # Redis
from synced_memory.dragonflydb import Memory  # DragonflyDB

mem1 = Memory(db_prefix="tenant1:")
mem1.data = "tenant 1 data"

mem2 = Memory(db_prefix="tenant2:")
mem2.data = "tenant 2 data"

print(mem1.data)  # "tenant 1 data"
print(mem2.data)  # "tenant 2 data"
```

## Environment-Based Prefixes

```python
import os
from synced_memory.redis import Memory      # Redis
from synced_memory.dragonflydb import Memory  # DragonflyDB

env = os.getenv('ENVIRONMENT', 'development')
mem = Memory(db_prefix=f'{env}:')
mem.config = {"env": env}
# development:config, staging:config, production:config
```

## Inspecting Keys

```bash
redis-cli KEYS "myapp:*"
```

```python
import redis

r = redis.Redis(host='localhost', port=6379)
keys = r.keys('myapp:*')
for key in keys:
    print(key.decode('utf-8'))
```

## Best Practices

1. Use descriptive prefixes: `myapp:prod:` is better than `mp:`
2. Include environment: `myapp:dev:`, `myapp:prod:`
3. End with a colon: makes individual keys more readable
4. Avoid special characters beyond `:` and `_`
