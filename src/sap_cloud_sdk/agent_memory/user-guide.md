# Agent Memory User Guide

This module provides a Python client for the SAP Agent Memory service (v1 API). It lets agents
store, retrieve, and semantically search persistent memories, and record conversation messages
grouped into logical message groups. The service handles vector embeddings automatically for memories — you store
plain text, and the service makes it searchable by meaning.

> [!NOTE]
> Memory extraction is the caller's responsibility. This client stores whatever text you pass
> as `content`; it does not extract or summarize memories from conversation text on its own.

## Table of Contents

- [Agent Memory User Guide](#agent-memory-user-guide)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Import](#import)
  - [Quick Start](#quick-start)
    - [Basic Setup](#basic-setup)
    - [Custom Configuration](#custom-configuration)
    - [Using the Context Manager](#using-the-context-manager)
  - [Core Concepts](#core-concepts)
    - [`agent_id`](#agent_id)
    - [`invoker_id`](#invoker_id)
  - [Multitenancy](#multitenancy)
    - [AccessStrategy](#accessstrategy)
    - [Configuring at client level](#configuring-at-client-level)
    - [SUBSCRIBER (default)](#subscriber-default)
    - [PROVIDER](#provider)
  - [Semantic Search: A Brief Primer](#semantic-search-a-brief-primer)
  - [Memories](#memories)
    - [Create a Memory](#create-a-memory)
    - [Get a Memory](#get-a-memory)
    - [Update a Memory](#update-a-memory)
    - [Delete a Memory](#delete-a-memory)
    - [List Memories](#list-memories)
      - [Content and metadata filtering](#content-and-metadata-filtering)
    - [Count Memories](#count-memories)
    - [Semantic Search](#semantic-search)
  - [Messages](#messages)
    - [Create a Message](#create-a-message)
    - [Get a Message](#get-a-message)
    - [Delete a Message](#delete-a-message)
    - [List Messages](#list-messages)
      - [Content and metadata filtering](#content-and-metadata-filtering-1)
  - [Data Models](#data-models)
    - [Enums](#enums)
  - [Error Handling](#error-handling)
  - [Admin — Retention Config](#admin--retention-config)
    - [Get Retention Config](#get-retention-config)
    - [Update Retention Config](#update-retention-config)
  - [Common Scenarios](#common-scenarios)
    - [Injecting relevant memories into an LLM prompt](#injecting-relevant-memories-into-an-llm-prompt)
    - [Persisting a conversation turn](#persisting-a-conversation-turn)
    - [Retrieving a full conversation thread](#retrieving-a-full-conversation-thread)
    - [Paginating through all memories](#paginating-through-all-memories)
    - [Paginating through all messages](#paginating-through-all-messages)
  - [Troubleshooting](#troubleshooting)
    - [`AgentMemoryConfigError` on startup](#agentmemoryconfigerror-on-startup)
    - [`list_memories()` or `list_messages()` returns fewer results than expected](#list_memories-or-list_messages-returns-fewer-results-than-expected)
    - [`search_memories()` returns no results](#search_memories-returns-no-results)
    - [`AgentMemoryNotFoundError` when fetching a resource](#agentmemorynotfounderror-when-fetching-a-resource)
    - [`AgentMemoryHttpError` with status 401](#agentmemoryhttperror-with-status-401)
  - [Configuration](#configuration)
    - [Service Binding](#service-binding)
      - [Mounted Secrets (Kubernetes)](#mounted-secrets-kubernetes)
      - [Environment Variables](#environment-variables)
      - [UAA JSON Schema](#uaa-json-schema)
  - [LangGraph Checkpointer](#langgraph-checkpointer)
    - [Prerequisites](#prerequisites)
    - [Import](#import-1)
    - [Usage with LangGraph StateGraph](#usage-with-langgraph-stategraph)
    - [Usage with LangChain create\_agent](#usage-with-langchain-create_agent)
    - [Thread TTL](#thread-ttl)
      - [Exposing TTL as a configurable parameter with `@agent_config`](#exposing-ttl-as-a-configurable-parameter-with-agent_config)

## Installation

See the [SAP Cloud SDK for Python installation guide](https://github.com/SAP/cloud-sdk-python#installation)
for setup instructions. The agent memory module is included automatically.

## Import

You can import specific classes:

```python
from sap_cloud_sdk.agent_memory import (
    create_client,
    AgentMemoryConfig,
    FilterDefinition,
    Memory,
    Message,
    MessageRole,
    RetentionConfig,
    SearchResult,
)
```

Or use a star import for convenience:

```python
from sap_cloud_sdk.agent_memory import *
```

## Quick Start

### Basic Setup

Use `create_client()` to get a client with automatic credential detection:

```python
from sap_cloud_sdk.agent_memory import create_client

client = create_client()

memories = client.list_memories(agent_id="my-agent", invoker_id="user-123")
print(f"Found {len(memories)} memories")
```

`create_client()` reads credentials from the `CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_*`
environment variables (or a mounted volume on BTP). See the
[Configuration](#configuration) section for the full variable table.

### Custom Configuration

There's also support for custom configuration if you want to specify credentials directly:

```python
from sap_cloud_sdk.agent_memory import create_client, AgentMemoryConfig

config = AgentMemoryConfig(
    base_url="https://<service-host>",
    token_url="https://<tenant>.authentication.<region>/oauth/token",
    client_id="<client-id>",
    client_secret="<client-secret>",
)
client = create_client(config=config)
```

### Using the Context Manager

The context manager is optional, but it is the easiest way to ensure the client is
closed even if an exception is raised:

```python
with create_client() as client:
    memories = client.list_memories(agent_id="my-agent", invoker_id="user-123")
```

To close the client manually, call `client.close()`.

`close()` is only for local cleanup. It does **not** commit, flush, or roll back data.
Each API call is independent and final once accepted by the service.

Calling methods after `close()` is supported.

## Core Concepts

### `agent_id`

A stable identifier for the agent that owns the data — for example `"hr-assistant"` or
`"support-bot"`. Chosen by the implementer; typically the name or ID of the AI agent.

### `invoker_id`

Identifies the user or caller associated with the data — for example a user ID from
the application's auth system. Memories and messages are scoped to the combination of
`agent_id` and `invoker_id`.

Neither value is validated by the service — they are free-form strings. Consistent use
across create, read, and search calls is the implementer's responsibility.

## Multitenancy

The Agent Memory service runs in a multi-tenant BTP environment. By default, every API
call uses a **subscriber-scoped token** — meaning data is isolated to the subscriber tenant
that your application serves. You control this behaviour with the `access_strategy` and
`tenant` keyword arguments available on every client method.

### AccessStrategy

```python
from sap_cloud_sdk.agent_memory import AccessStrategy
```

| Value                       | Description                                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `SUBSCRIBER` (default) | Reads and writes against the subscriber tenant. Requires `tenant`.                                            |
| `PROVIDER`             | Reads and writes against the provider tenant. No `tenant` needed. Caution: this provides no tenant isolation. |

### Configuring at client level

Pass `access_strategy` and `tenant` to `create_client()` to set defaults for the entire
client instance. Every method call then inherits them, so you do not need to repeat them
on each operation.

```python
from sap_cloud_sdk.agent_memory import create_client, AccessStrategy

# Tenant set once — all calls below use it automatically
client = create_client(
    access_strategy=AccessStrategy.SUBSCRIBER,
    tenant="acme-corp",
)

memories = client.list_memories(agent_id="hr-assistant", invoker_id="user-42")
count    = client.count_memories(agent_id="hr-assistant")
```

### SUBSCRIBER (default)

Configure a subscriber tenant at client creation. All calls will use that tenant context.

```python
client = create_client(
    access_strategy=AccessStrategy.SUBSCRIBER,
    tenant="acme-corp",
)
memories = client.list_memories(agent_id="hr-assistant", invoker_id="user-42")
```

### PROVIDER

Configure a provider-only client. No tenant is needed; all calls use the provider binding.

```python
client = create_client(access_strategy=AccessStrategy.PROVIDER)
memories = client.list_memories(agent_id="hr-assistant", invoker_id="user-42")
```

> [!WARNING]
> `PROVIDER` provides **no tenant isolation** — the provider token grants access to data across all subscriber tenants Only use this strategy for provider-owned operations (e.g., admin tasks, shared datasets). Never use it to serve subscriber-specific data.

## Semantic Search: A Brief Primer

Texts with different words — or even different languages — can have the same meaning.
"How to make pizza dough?" and "Italian flatbread preparation steps" are semantically similar
despite sharing no words. To search a large corpus by meaning rather than exact keywords, the
service uses vector embeddings.

An embedding model translates a text into a high-dimensional numeric vector. Texts with similar
meaning produce vectors that point in a similar direction. The cosine similarity between two
vectors measures that directional closeness: a value near 1.0 means the texts are semantically
similar.

Example corpus:

- "Trains cross bridges"
- "Clouds block sunlight"
- "Rivers carve valleys"
- "Wolves hunt deer"
- "Engines power ships"

A search for "Sky illumination" returns "Clouds block sunlight" — closest in meaning, with the
highest cosine similarity — even though the query shares no words with the result.

`search_memories()` uses this mechanism: you pass a natural-language query and a similarity
threshold, and the service returns the most semantically relevant stored memories.

## Memories

Memories are persistent knowledge entries scoped to an `agent_id` + `invoker_id` pair.
The service generates a vector embedding for each memory automatically, enabling semantic search.

### Create a Memory

```python
memory = client.add_memory(
    agent_id="my-agent",
    invoker_id="user-123",
    content="The user prefers dark mode and metric units.",
    metadata={"source": "preferences"},
)
print(memory.id)
# "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

**Required fields:**

- `agent_id`: Identifier of the agent that owns this memory.
- `invoker_id`: Identifier of the user or caller associated with this memory.
- `content`: The memory text (plain string).

**Optional fields:**

- `metadata`: Arbitrary key-value dict stored alongside the memory.

### Get a Memory

```python
memory = client.get_memory(memory_id="<uuid>")
print(memory.content)
# "The user prefers dark mode and metric units."
```

### Update a Memory

`update_memory` performs a partial update;
omitted fields remain untouched.

> [!NOTE]
> `content` and `metadata` are the only editable fields; `memory_id` identifies which memory to update and cannot be modified

```python
client.update_memory(
    memory_id="<uuid>",
    content="user prefers dark mode, metric units, and large font.",
    metadata={"source": "preferences", "version": 2},
)
```

### Delete a Memory

```python
client.delete_memory(memory_id="<uuid>")
```

### List Memories

```python
memories = client.list_memories(
    agent_id="my-agent",
    invoker_id="user-123",
    limit=20,
)
for m in memories:
    print(f"  [{m.id}] {m.content[:80]}")
# [a1b2c3d4-...] The user prefers dark mode and metric units.
# [b2c3d4e5-...] The user's timezone is Europe/Berlin.
```

**Parameters:**

| Parameter    | Type                               | Default | Description                                       |
| ------------ | ---------------------------------- | ------- | ------------------------------------------------- |
| `agent_id`   | `str` \| `None`                    | `None`  | Filter by agent identifier.                       |
| `invoker_id` | `str` \| `None`                    | `None`  | Filter by invoker/user identifier.                |
| `filters`    | `list[FilterDefinition]` \| `None` | `None`  | Substring filters on `"content"` or `"metadata"`. |
| `limit`      | `int`                              | `50`    | Maximum number of memories to return.             |
| `offset`     | `int`                              | `0`     | Number of memories to skip (pagination).          |

**Returns:** `list[Memory]`

#### Content and metadata filtering

Use `FilterDefinition` to narrow results by substring. Import it alongside `create_client`:

```python
from sap_cloud_sdk.agent_memory import create_client, FilterDefinition

# Memories whose content contains "dark mode"
memories = client.list_memories(
    agent_id="my-agent",
    invoker_id="user-123",
    filters=[FilterDefinition(target="content", contains="dark mode")],
)

# Combined: content AND metadata must both match
memories = client.list_memories(
    agent_id="my-agent",
    invoker_id="user-123",
    filters=[
        FilterDefinition(target="content", contains="dark mode"),
        FilterDefinition(target="metadata", contains="preferences"),
    ],
)
```

`target` must be `"content"` or `"metadata"`. Multiple clauses are combined with AND.

> [!WARNING]
> Defining two clauses with the **same target** produces an AND predicate that requires
> both substrings to be present in the same field simultaneously. This is rarely
> intentional — for example:
>
> ```python
> filters=[
>     FilterDefinition(target="content", contains="user prefers"),
>     FilterDefinition(target="content", contains="user doesn't prefer"),
> ]
> ```
>
> Only memories whose content contains _both_ substrings will be returned, which is
> typically an empty result set. OR combining across clauses is not yet supported.

> [!NOTE]
> Metadata is stored as a JSON string. Filtering on `"metadata"` performs a free-text
> substring match on the raw JSON — for example `contains="preferences"` matches any
> metadata whose serialized form includes that word. Structured key-value filtering
> (e.g. `metadata.source == "preferences"`) is not supported.

### Count Memories

Count memories without fetching their content. Near-zero cost.

```python
total = client.count_memories(agent_id="my-agent", invoker_id="user-123")
print(f"Total memories: {total}")
# Total memories: 42
```

**Parameters:**

| Parameter    | Type            | Default | Description                        |
| ------------ | --------------- | ------- | ---------------------------------- |
| `agent_id`   | `str` \| `None` | `None`  | Filter by agent identifier.        |
| `invoker_id` | `str` \| `None` | `None`  | Filter by invoker/user identifier. |

**Returns:** `int`

### Semantic Search

Search for memories whose meaning is similar to a natural-language query. The service returns
results ordered by relevance (highest similarity first).

```python
results = client.search_memories(
    agent_id="my-agent",
    invoker_id="user-123",
    query="What are the user's display preferences?",
    threshold=0.6,
    limit=5,
)
for r in results:
    print(f"[similarity={r.similarity:.2f}] {r.content}")
# [similarity=0.92] The user prefers dark mode and metric units.
# [similarity=0.81] User last asked about display settings on 2025-01-10.
```

**Parameters:**

| Parameter    | Type    | Default | Description                                        |
| ------------ | ------- | ------- | -------------------------------------------------- |
| `agent_id`   | `str`   | —       | Agent identifier to scope the search.              |
| `invoker_id` | `str`   | —       | Invoker/user identifier to scope the search.       |
| `query`      | `str`   | —       | Natural-language search query (5–5000 characters). |
| `threshold`  | `float` | `0.6`   | Minimum cosine similarity score (0.0–1.0).         |
| `limit`      | `int`   | `10`    | Maximum number of results (1–50).                  |

**Returns:** `list[SearchResult]` — each result extends `Memory` with a `similarity` (cosine score) field.

---

## Messages

Messages represent individual turns in a conversation. Messages sharing the same `message_group`
form a logical message group. The service does not enforce a session concept — grouping is done
entirely via the `message_group` value you choose.

### Create a Message

```python
from sap_cloud_sdk.agent_memory import MessageRole

message = client.add_message(
    agent_id="my-agent",
    invoker_id="user-123",
    message_group="conv-001",
    role=MessageRole.USER,
    content="What is the weather like today?",
)
print(message.id)
# "c3d4e5f6-a1b2-..."
```

**Required fields:**

- `agent_id`: Identifier of the agent.
- `invoker_id`: Identifier of the user or caller.
- `message_group`: Message group identifier (any string; use a consistent value per conversation).
- `role`: Author role — use the `MessageRole` enum: `USER`, `ASSISTANT`, `SYSTEM`, `TOOL`.
- `content`: The message text.

**Optional fields:**

- `metadata`: Arbitrary key-value dict stored alongside the message.

### Get a Message

```python
message = client.get_message(message_id="<uuid>")
print(f"[{message.role}] {message.content}")
# [USER] What is the weather like today?
```

### Delete a Message

```python
client.delete_message(message_id="<uuid>")
```

### List Messages

```python
messages = client.list_messages(
    agent_id="my-agent",
    invoker_id="user-123",
    message_group="conv-001",
    limit=50,
)
for msg in messages:
    print(f"  [{msg.role}] {msg.content[:80]}")
# [USER] What is the weather like today?
# [ASSISTANT] It's sunny and 22°C in Berlin.
```

Filter by role to retrieve only a specific author's turns:

```python
user_messages = client.list_messages(
    agent_id="my-agent",
    invoker_id="user-123",
    message_group="conv-001",
    role=MessageRole.USER,
)
```

**Parameters:**

| Parameter       | Type                               | Default | Description                                       |
| --------------- | ---------------------------------- | ------- | ------------------------------------------------- |
| `agent_id`      | `str` \| `None`                    | `None`  | Filter by agent identifier.                       |
| `invoker_id`    | `str` \| `None`                    | `None`  | Filter by invoker/user identifier.                |
| `message_group` | `str` \| `None`                    | `None`  | Filter by conversation group.                     |
| `role`          | `str` \| `None`                    | `None`  | Filter by author role (USER, ASSISTANT, …).       |
| `filters`       | `list[FilterDefinition]` \| `None` | `None`  | Substring filters on `"content"` or `"metadata"`. |
| `limit`         | `int`                              | `50`    | Maximum number of messages to return.             |
| `offset`        | `int`                              | `0`     | Number of messages to skip (pagination).          |

**Returns:** `list[Message]`

#### Content and metadata filtering

The same `FilterDefinition` syntax applies to messages:

```python
from sap_cloud_sdk.agent_memory import create_client, FilterDefinition

# Messages whose metadata contains a specific tag
messages = client.list_messages(
    agent_id="my-agent",
    invoker_id="user-123",
    message_group="conversation-001",
    filters=[FilterDefinition(target="metadata", contains="escalated")],
)

# Messages whose content mentions a keyword
messages = client.list_messages(
    agent_id="my-agent",
    invoker_id="user-123",
    filters=[FilterDefinition(target="content", contains="invoice")],
)
```

See the [Content and metadata filtering](#content-and-metadata-filtering) note under
[List Memories](#list-memories) for details on metadata free-text limitations.

---

## Data Models

| Model             | Description                                                                                           |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| `Memory`          | A persistent memory entry (`id`, `agent_id`, `invoker_id`, `content`, `metadata`, timestamps)         |
| `SearchResult`    | Extends `Memory` with a `similarity` field (cosine score, 0–1)                                        |
| `Message`         | A message (`id`, `agent_id`, `invoker_id`, `message_group`, `role`, `content`, `metadata`, timestamp) |
| `RetentionConfig` | Data retention policy (`message_days`, `memory_days`, `usage_log_days`, timestamps)                   |

### Enums

| Enum             | Values                                       |
| ---------------- | -------------------------------------------- |
| `MessageRole`    | `USER`, `ASSISTANT`, `SYSTEM`, `TOOL`        |
| `AccessStrategy` | `SUBSCRIBER` (default), `PROVIDER` |

All models expose a `to_dict()` method that returns a plain dict for logging or forwarding.

```python
memory = client.get_memory(memory_id="a1b2c3d4-...")
print(memory.to_dict())
# {
#   "id": "a1b2c3d4-...",
#   "agent_id": "my-agent",
#   "invoker_id": "user-123",
#   "content": "The user prefers dark mode and metric units.",
#   "metadata": {},
#   "created_at": "2025-01-10T12:00:00Z",
#   "updated_at": "2025-01-10T12:00:00Z",
# }
```

---

## Error Handling

The module defines a structured exception hierarchy so you can catch errors at the appropriate
level of specificity:

```
AgentMemoryError
├── AgentMemoryConfigError      # bad or missing configuration
├── AgentMemoryValidationError  # invalid inputs caught before any network call
└── AgentMemoryHttpError        # HTTP-level error (status_code, response_text)
    └── AgentMemoryNotFoundError  # 404 Not Found
```

```python
from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryError,
    AgentMemoryConfigError,
    AgentMemoryValidationError,
    AgentMemoryHttpError,
    AgentMemoryNotFoundError,
)

# Catch invalid inputs before they reach the network
try:
    client.add_memory(agent_id="", invoker_id="user-123", content="hello")
except AgentMemoryValidationError as e:
    print(f"Bad input: {e}")
# Bad input: Required field(s) must be non-empty: 'agent_id'

# Catch a specific 404
try:
    memory = client.get_memory(memory_id="non-existent-id")
except AgentMemoryNotFoundError:
    print("Memory not found")

# Inspect the HTTP status code and response body
try:
    memories = client.list_memories(agent_id="my-agent")
except AgentMemoryHttpError as e:
    print(f"HTTP {e.status_code}: {e.response_text}")

# Catch all Agent Memory errors
try:
    client = create_client()
    memories = client.list_memories(agent_id="my-agent")
except AgentMemoryError as e:
    print(f"Agent Memory error: {e}")
```

---

## Admin — Retention Config

The retention configuration controls automatic data cleanup. It is a singleton — one config
per tenant.

### Get Retention Config

```python
rc = client.get_retention_config()
print(f"Messages: {rc.message_days} days")
print(f"Memories: {rc.memory_days} days")
print(f"Usage logs: {rc.usage_log_days} days")
```

### Update Retention Config

`update_retention_config` performs a partial update — only the provided fields are
changed; omitted fields remain unchanged.

```python
client.update_retention_config(
    message_days=30,
    memory_days=90,
    usage_log_days=180,
)
```

Set a field to `0` to mark all data in that category for deletion at the next nightly scheduled cleanup. The server also accepts `null` to disable
automatic cleanup for that category.

**When changes take effect**

The service runs nightly data cleanup procedures that delete records based on creation timestamp. Changes to retention configuration apply to all future retention sweeps. The new retention window is calculated from each record's original creation timestamp, not from the time of the config change.

_Increasing retention_ — records that were approaching expiry get more time. For example,
if `message_days` is raised from 90 to 120, a message created 89 days ago will now be
retained until it reaches 120 days old rather than being cleaned up after 90 days.

_Decreasing retention_ — records outside the new window become eligible for removal. For
example, if `message_days` is reduced from 90 to 30, messages older than 30 days will be
removed at the next retention sweep, even if they fell within the original 90-day limit
when they were created.

> [!WARNING]
> Decreasing a retention period is a destructive, irreversible operation. Records outside
> the new window are permanently deleted at the next cleanup sweep.

---

## Common Scenarios

### Injecting relevant memories into an LLM prompt

Retrieve the most semantically relevant past memories before calling the language model:

```python
def build_context(client, agent_id, invoker_id, user_query):
    results = client.search_memories(
        agent_id=agent_id,
        invoker_id=invoker_id,
        query=user_query,
        threshold=0.65,
        limit=5,
    )
    if not results:
        return ""
    lines = [f"- {r.content}" for r in results]
    return "Relevant context from memory:\n" + "\n".join(lines)
```

### Persisting a conversation turn

Store each user and assistant message so the full conversation history is available:

```python
def record_turn(client, agent_id, invoker_id, group_id, user_text, assistant_text):
    client.add_message(
        agent_id=agent_id,
        invoker_id=invoker_id,
        message_group=group_id,
        role=MessageRole.USER,
        content=user_text,
    )
    client.add_message(
        agent_id=agent_id,
        invoker_id=invoker_id,
        message_group=group_id,
        role=MessageRole.ASSISTANT,
        content=assistant_text,
    )
```

### Retrieving a full conversation thread

```python
def get_conversation(client, agent_id, invoker_id, group_id):
    return client.list_messages(
        agent_id=agent_id,
        invoker_id=invoker_id,
        message_group=group_id,
        limit=100,
    )
```

### Paginating through all memories

`list_memories` returns at most `limit` results per call. Use `offset` to page through large
sets, or use `count_memories` first to decide whether pagination is even necessary:

```python
PAGE_SIZE = 100

total = client.count_memories(agent_id="my-agent", invoker_id="user-123")
if total == 0:
    memories = []
elif total <= PAGE_SIZE:
    memories = client.list_memories(
        agent_id="my-agent", invoker_id="user-123", limit=total
    )
else:
    def iter_all_memories(client, agent_id, invoker_id, page_size=PAGE_SIZE):
        offset = 0
        while True:
            page = client.list_memories(
                agent_id=agent_id,
                invoker_id=invoker_id,
                limit=page_size,
                offset=offset,
            )
            yield from page
            if len(page) < page_size:
                break
            offset += page_size

    memories = list(iter_all_memories(client, "my-agent", "user-123"))
```

### Paginating through all messages

```python
def iter_all_messages(client, agent_id, invoker_id, message_group, page_size=100):
    offset = 0
    while True:
        page = client.list_messages(
            agent_id=agent_id,
            invoker_id=invoker_id,
            message_group=message_group,
            limit=page_size,
            offset=offset,
        )
        yield from page
        if len(page) < page_size:
            break
        offset += page_size
```

---

## Troubleshooting

### `AgentMemoryConfigError` on startup

```
AgentMemoryConfigError: Failed to load configuration: ...
```

Credentials could not be found. Check that either:

- The BTP service binding is mounted at `/etc/secrets/appfnd/hana-agent-memory/default/`
- Or the environment variables are set (see [Configuration](#configuration))

### `list_memories()` or `list_messages()` returns fewer results than expected

The default `limit` is `50`. Increase it or paginate:

```python
memories = client.list_memories(agent_id="my-agent", invoker_id="user-123", limit=200)
```

Also verify `agent_id` and `invoker_id` exactly match the values used when the memories were created.

### `search_memories()` returns no results

The default `threshold` of `0.6` may be too strict for your data. Try a lower value:

```python
results = client.search_memories(
    agent_id="my-agent", invoker_id="user-123",
    query="user display preferences",
    threshold=0.3,
)
```

### `AgentMemoryNotFoundError` when fetching a resource

The resource was deleted, the ID is incorrect, or the `agent_id`/`invoker_id` passed to a
list or search operation does not match the values used when the resource was created.

### `AgentMemoryHttpError` with status 401

The OAuth2 token has expired and automatic refresh failed, or the configured credentials
(`client_id`, `client_secret`, `token_url`) are incorrect. Verify the credentials in your
environment variables or service binding.

---

## Configuration

### Service Binding

- **Mount path**: `$SERVICE_BINDING_ROOT/hana-agent-memory/default/` (defaults to `/etc/secrets/appfnd/hana-agent-memory/default/`)
- **Required keys**: `application_url` (Agent Memory service URL), `uaa` (JSON string with XSUAA credentials)
- **Env var fallback**: `CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_{FIELD}` (uppercased)

> **Note:** `SERVICE_BINDING_ROOT` defaults to `/etc/secrets/appfnd` when not set. See the [Secret Resolver guide](../core/secret_resolver/user-guide.md) for details.

#### Mounted Secrets (Kubernetes)

```
$SERVICE_BINDING_ROOT/hana-agent-memory/default/
├── application_url
└── uaa
```

#### Environment Variables

```bash
export CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL="https://agent-memory.example.com"
export CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA='{"clientid":"...","clientsecret":"...","url":"https://..."}'
```

#### UAA JSON Schema

The `uaa` key must contain a JSON string with the XSUAA credentials:

```json
{
  "clientid": "sb-xxx",
  "clientsecret": "xxx",
  "url": "https://subdomain.authentication.region.hana.ondemand.com"
}
```

## LangGraph Checkpointer

> This section covers the LangGraph-specific
> factory for short-term memory (checkpointing). It is only relevant if your agent
> is built with LangGraph or LangChain's `create_agent()`. The core
> `AgentMemoryClient` and `create_client()` above are framework-agnostic and work
> independently of this section.

For LangGraph agents, the `agent_memory` module provides a `create_checkpointer()`
factory in the `factory` subpackage. It returns a `BaseCheckpointSaver` that
manages short-term session memory — conversation state, thread continuity, and
HITL support — natively within LangGraph.

> [!NOTE]
> The current implementation uses LangGraph's `InMemorySaver` or
> `TimedInMemorySaver` (when `ttl_seconds` is set). State is held in-process
> and does not survive restarts. Persistent checkpointing backed by the
> Agent Memory Service is not yet supported.

### Prerequisites

`langgraph` is an optional dependency. Install it via the SDK extra or directly:

```bash
# Via SDK optional extra (recommended)
pip install "sap-cloud-sdk[langgraph]"

# Or install langgraph directly
pip install langgraph
```

### Import

```python
from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer
```

### Usage with LangGraph StateGraph

```python
from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer

checkpointer = create_checkpointer()
app = workflow.compile(checkpointer=checkpointer)

result = app.invoke(
    {"messages": [{"role": "user", "content": "hello"}]},
    {"configurable": {"thread_id": "session-1"}},
)
```

### Usage with LangChain create_agent

```python
from langchain.agents import create_agent
from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer

agent = create_agent(
    model="...",
    tools=[...],
    checkpointer=create_checkpointer(),
)
```

### Thread TTL

Pass `ttl_seconds` to evict threads that have been inactive for the given
period. This prevents unbounded memory growth in long-running processes.

```python
# Evict threads inactive for more than 1 hour
checkpointer = create_checkpointer(ttl_seconds=3600)
```

When `ttl_seconds` is set, the factory returns a `TimedInMemorySaver` that
tracks last-active time per thread and evicts inactive threads via a
background daemon sweep. Eviction is best-effort — a thread may live up to
`ttl_seconds + 60` seconds before deletion.

#### Exposing TTL as a configurable parameter with `@agent_config`

Use `@agent_config` from `sap_cloud_sdk.agent_decorators` to expose
`ttl_seconds` as an operator-adjustable configuration field. The key
`config.checkpointer.ttl_seconds` groups it with other checkpointer settings
so external tooling can surface it in the low-code UI alongside model
selection and temperature.

```python
from sap_cloud_sdk.agent_decorators import agent_config
from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer


@agent_config(
    key="config.checkpointer.ttl_seconds",
    label="Thread TTL (seconds)",
    description="Evict inactive conversation threads after this period of "
                "inactivity. Set to 0 to disable eviction.",
)
def thread_ttl_seconds() -> int:
    return 3600 # 1 hour


class MyAgent:
    def __init__(self):
        ttl = thread_ttl_seconds()
        self._checkpointer = create_checkpointer(ttl_seconds=ttl or None)
```

> [!NOTE]
> `TimedInMemorySaver` state does not survive process restarts — the TTL
> applies to in-process memory only. Persistent TTL enforcement will be
> available when the Agent Memory Service checkpointer ships.
