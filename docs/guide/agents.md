# Scoped Memory

synced-memory provides `PrefixedMemory` to isolate memory by a custom scope
prefix — multiple scopes can share the same backend safely.

## PrefixedMemory Class

```python
from synced_memory.redis import PrefixedMemory      # Redis
from synced_memory.dragonflydb import PrefixedMemory  # DragonflyDB

mem = PrefixedMemory(prefix="session_abc")
```

## Basic Usage

```python
from synced_memory.redis import PrefixedMemory      # Redis
from synced_memory.dragonflydb import PrefixedMemory  # DragonflyDB

mem = PrefixedMemory(prefix="user_123")

mem.messages = [
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi! How can I help you?"}
]
mem.user_name = "Alice"
```

## Accessing from Different Processes

```python
# Process 1
mem = PrefixedMemory(prefix="scope_123")
mem.messages.append({"role": "user", "content": "What's the weather?"})

# Process 2 (different worker/pod)
mem2 = PrefixedMemory(prefix="scope_123")
print(mem2.messages)  # includes the message from Process 1
```

## Integration with LLM Frameworks

### LiteLLM

```python
from synced_memory.redis import PrefixedMemory      # Redis
from synced_memory.dragonflydb import PrefixedMemory  # DragonflyDB
import litellm

mem = PrefixedMemory(prefix="session_xyz")

if not hasattr(mem, 'messages'):
    mem.messages = []

mem.messages.append({"role": "user", "content": "Hello!"})

response = litellm.completion(
    model="gpt-4o",
    messages=mem.messages.aslist()  # pass plain list to LiteLLM
)

mem.messages.append({
    "role": "assistant",
    "content": response.choices[0].message.content
})
```

## Multi-Agent Systems

```python
from synced_memory.redis import PrefixedMemory      # Redis
from synced_memory.dragonflydb import PrefixedMemory  # DragonflyDB

# Agent 1: Intent Classifier
mem = PrefixedMemory(prefix="multi_agent_session")
mem.detected_intent = "technical_support"

# Agent 2: Router (different process)
mem2 = PrefixedMemory(prefix="multi_agent_session")
if mem2.detected_intent == "technical_support":
    mem2.assigned_specialist = "tech_agent_3"

# Agent 3: Specialist (different process)
mem3 = PrefixedMemory(prefix="multi_agent_session")
if hasattr(mem3, 'assigned_specialist'):
    mem3.resolution_status = "in_progress"
```

## Best Practices

1. Use unique prefixes (UUIDs, session tokens, or user IDs)
2. Pass `.aslist()` / `.asdict()` to LLM libraries that may `deepcopy` the data
3. Trim message history to manage context window limits
4. Clean up old scopes to avoid unbounded backend growth
