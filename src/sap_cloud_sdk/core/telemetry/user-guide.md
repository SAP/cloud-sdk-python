# Telemetry User Guide

## What it does

- **Auto-instruments AI frameworks** - automatic tracing
- **Creates custom spans** - wrap your code to trace operations and add context
- **Tracks tenant IDs** - per-request tenant tracking in traces and metrics

## How to use it

### Auto-instrument AI frameworks

Call before importing AI libraries:

```python
from sap_cloud_sdk.core.telemetry import auto_instrument

auto_instrument()

from litellm import completion
# All LLM calls are now automatically traced
```

### Create custom spans

Wrap operations to trace them:

```python
from sap_cloud_sdk.core.telemetry import context_overlay, GenAIOperation

with context_overlay(GenAIOperation.CHAT):
    response = llm.chat(message)
```

Add custom attributes:

```python
with context_overlay(
    GenAIOperation.CHAT,
    attributes={"user.id": "123", "feature": "support"}
):
    response = llm.chat(message)
```

Available operations:

```python
GenAIOperation.CHAT                 # Chat completion
GenAIOperation.TEXT_COMPLETION      # Text completion
GenAIOperation.EMBEDDINGS          # Embedding generation
GenAIOperation.GENERATE_CONTENT    # Multimodal content generation
GenAIOperation.RETRIEVAL           # Document/context retrieval
GenAIOperation.EXECUTE_TOOL        # Tool execution
GenAIOperation.CREATE_AGENT        # Agent creation
GenAIOperation.INVOKE_AGENT        # Agent invocation
```

Nest spans for complex workflows:

```python
with context_overlay(GenAIOperation.RETRIEVAL):
    documents = retrieve_documents(query)

    with context_overlay(GenAIOperation.CHAT):
        response = llm.chat(messages=[
            {"role": "system", "content": f"Context: {documents}"},
            {"role": "user", "content": query}
        ])
```

### Propagate attributes to child spans

Use `propagate=True` to automatically pass attributes from a parent span to all child spans within its scope. This is useful for cross-cutting attributes like `gen_ai.conversation.id`, `gen_ai.agent.name`, or custom keys that should appear on every nested span without repeating them.

```python
with context_overlay(
    GenAIOperation.INVOKE_AGENT,
    attributes={"gen_ai.conversation.id": "conv-123", "user.id": "u-456"},
    propagate=True
):
    # Both child spans automatically receive gen_ai.conversation.id and user.id
    with chat_span(model="gpt-4", provider="openai") as span:
        response = client.chat.completions.create(...)

    with execute_tool_span(tool_name="get_weather"):
        result = call_weather_api(location)
```

All four span functions support `propagate=True`: `context_overlay`, `chat_span`, `execute_tool_span`, and `invoke_agent_span`.

**Priority rules** — child spans always win over propagated values (highest to lowest):
1. Required semantic keys set by the span function (e.g. `gen_ai.operation.name`) — always wins
2. User-provided `attributes` on the child span
3. Propagated attrs from ancestors — lowest priority, easily overridden

```python
# Even if the parent propagated gen_ai.operation.name="invoke_agent",
# the child chat_span always sets it to "chat"
with invoke_agent_span(provider="openai", propagate=True):
    with chat_span(model="gpt-4", provider="openai") as span:
        pass  # span has gen_ai.operation.name="chat", not "invoke_agent"
```

Propagation is scoped: once the `propagate=True` span exits, its attributes are no longer passed to subsequent sibling spans.

Nesting multiple `propagate=True` spans accumulates attributes from all levels:

```python
with context_overlay(GenAIOperation.INVOKE_AGENT, attributes={"session": "s1"}, propagate=True):
    with chat_span("gpt-4", "openai", attributes={"turn": "1"}, propagate=True):
        with execute_tool_span("search"):
            pass  # receives both session="s1" and turn="1"
```

### Add events to spans

```python
with context_overlay(GenAIOperation.EMBEDDINGS) as span:
    span.add_event("preprocessing_started")
    text = preprocess_text(raw_text)
    
    span.add_event("embedding_generation_started")
    embeddings = generate_embeddings(text)
    
    span.add_event("completed", attributes={
        "embedding_dim": len(embeddings)
    })
```

### GenAI-specific spans

For LLM calls following [OpenTelemetry GenAI conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/):

```python
from sap_cloud_sdk.core.telemetry import chat_span, execute_tool_span, invoke_agent_span

# LLM chat calls
with chat_span(model="gpt-4", provider="openai", conversation_id="cid") as span:
    response = client.chat.completions.create(...)

# Tool execution
with execute_tool_span(tool_name="get_weather", tool_type="mcp", tool_description="weather mcp server"):
    result = call_weather_api(location)

# Agent invocation
with invoke_agent_span(provider="openai", agent_name="SupportBot", agent_id="id", agent_description="support agent", conversation_id="cid"):
    response = client.beta.threads.runs.create(...)
```

### Track tenant ID

Set at request entry point:

```python
from sap_cloud_sdk.core.telemetry import set_tenant_id

def handle_request(request):
    tenant_id = extract_tenant_from_jwt(request)
    set_tenant_id(tenant_id)
```

Thread-safe and async-safe. Automatic Propagation.

### Access current span

```python
from sap_cloud_sdk.core.telemetry import get_current_span, add_span_attribute

span = get_current_span()
if span.is_recording():
    span.set_attribute("custom.key", "value")

# Or use the helper
add_span_attribute("request.id", request_id)
```

## Configuration

### Production

For production environments, you should ensure that `OTEL_EXPORTER_OTLP_ENDPOINT` is configured and points to the expected OTLP endpoint. This variable is a standard environment variable from the OpenTelemetry libraries.

### Local Development

To print traces directly to the console without an OTLP collector, set:

```bash
export OTEL_TRACES_EXPORTER=console
```

Then call `auto_instrument()` as usual — traces will be printed to stdout.

To use an OTLP collector instead:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otel-collector.example.com"
```

### System Role

Set via environment variable:

```bash
export APPFND_CONHOS_SYSTEM_ROLE="S4HC"
```

## Complete Example

```python
from sap_cloud_sdk.core.telemetry import (
    auto_instrument,
    context_overlay,
    GenAIOperation,
    set_tenant_id,
    add_span_attribute
)

auto_instrument()

from litellm import completion

async def handle_customer_query(query: str, user_id: str):
    set_tenant_id("bh7sjh...")
    
    with context_overlay(
        GenAIOperation.RETRIEVAL,
        attributes={"user.id": user_id, "query.type": "support"}
    ):
        documents = await retrieve_knowledge_base(query)
        add_span_attribute("documents.count", len(documents))
        
        with context_overlay(GenAIOperation.CHAT):
            response = completion(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"Context: {documents}"},
                    {"role": "user", "content": query}
                ]
            )
            add_span_attribute("response.length", len(response.choices[0].message.content))
        
        return response
