# Agent Memory

synced-memory provides `ConversationMemory` for conversational AI agents — it namespaces
all keys by a conversation ID so multiple conversations can share the same backend safely.

## ConversationMemory Class

```python
from synced_memory.redis import ConversationMemory
import uuid

conversation_id = str(uuid.uuid4())
mem = ConversationMemory(conversation_id=conversation_id)
```

## Basic Usage

```python
from synced_memory.redis import ConversationMemory

conv_id = "conversation_123"
mem = ConversationMemory(conversation_id=conv_id)

mem.messages = [
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi! How can I help you?"}
]
mem.user_name = "Alice"
```

## Accessing from Different Processes

```python
# Agent Process 1
mem = ConversationMemory(conversation_id="conv_123")
mem.messages.append({"role": "user", "content": "What's the weather?"})

# Agent Process 2 (different worker/pod)
mem2 = ConversationMemory(conversation_id="conv_123")
print(mem2.messages)  # includes the message from Process 1
```

## Integration with LLM Frameworks

### LiteLLM

```python
from synced_memory.redis import ConversationMemory
import litellm

conv_id = "session_xyz"
mem = ConversationMemory(conversation_id=conv_id)

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
from synced_memory.redis import ConversationMemory

conv_id = "multi_agent_session"

# Agent 1: Intent Classifier
mem = ConversationMemory(conversation_id=conv_id)
mem.detected_intent = "technical_support"

# Agent 2: Router (different process)
mem2 = ConversationMemory(conversation_id=conv_id)
if mem2.detected_intent == "technical_support":
    mem2.assigned_specialist = "tech_agent_3"

# Agent 3: Specialist (different process)
mem3 = ConversationMemory(conversation_id=conv_id)
if hasattr(mem3, 'assigned_specialist'):
    mem3.resolution_status = "in_progress"
```

## Best Practices

1. Use unique conversation IDs (UUIDs or session tokens)
2. Pass `.aslist()` / `.asdict()` to LLM libraries that may `deepcopy` the data
3. Trim message history to manage context window limits
4. Clean up old conversations to avoid unbounded backend growth
