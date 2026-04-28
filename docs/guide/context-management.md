# Context Management

synced-memory supports Python's context manager protocol.

## Basic Usage

```python
from synced_memory.redis import Memory

with Memory() as memory:
    memory.session = "active"
    memory.user_id = 12345
    print(memory.session)  # "active"
```

When the `with` block exits, any remaining queued writes are flushed and the background
thread is stopped cleanly.

## Persistence Across Contexts

Values written inside a context block persist in the backend and are visible to any
subsequent instance:

```python
with Memory() as memory:
    memory.test_key = "hello world"

with Memory() as memory:
    print(memory.test_key)  # "hello world"
```

## Exception Safety

Cleanup runs even if an exception is raised:

```python
try:
    with Memory() as memory:
        memory.status = "processing"
        result = risky_operation()
        memory.status = "completed"
except Exception as e:
    print(f"Operation failed: {e}")
    # memory is properly cleaned up
```

## Combining with Other Context Managers

```python
from synced_memory.redis import Memory

with Memory() as memory, open('log.txt', 'w') as log_file:
    memory.session_id = "abc123"
    log_file.write(f"Session: {memory.session_id}\n")
```

## Without Context Managers

Context managers are optional. Direct instantiation works fine:

```python
mem = Memory()
mem.value = "test"
# Memory object lives until garbage collected
```

## Async Code

Memory operations are synchronous (blocking). Use them outside of async-critical
paths or run them in a thread pool:

```python
import asyncio
from synced_memory.redis import Memory

async def async_task():
    with Memory() as memory:
        memory.task_status = "running"
        await asyncio.sleep(1)
        memory.task_status = "completed"

asyncio.run(async_task())
```
