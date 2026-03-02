# Telemetry User Guide

## What it does

- **Auto-instruments AI frameworks** - automatic tracing
- **Creates custom spans** - wrap your code to trace operations and add context
- **Records metrics** - token usage for LLM calls
- **Tracks tenant IDs** - per-request tenant tracking in traces and metrics

## How to use it

### Auto-instrument AI frameworks

Call before importing AI libraries:

```python
from cloud_sdk_python.core.telemetry import auto_instrument

auto_instrument()

from litellm import completion
# All LLM calls are now automatically traced
```

### Create custom spans

Wrap operations to trace them:

```python
from cloud_sdk_python.core.telemetry import context_overlay, GenAIOperation

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

Add events to spans:

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
from cloud_sdk_python.core.telemetry import chat_span, execute_tool_span, invoke_agent_span

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

### Record token metrics

```python
from cloud_sdk_python.core.telemetry import record_aicore_metric

record_aicore_metric(
    model_name="gpt-4",
    provider="openai",
    operation_name="chat",
    input_tokens=150,
    output_tokens=75
)
```

With custom attributes:

```python
record_aicore_metric(
    model_name="gpt-4",
    provider="openai",
    operation_name="chat",
    input_tokens=150,
    output_tokens=75,
    custom_attributes={
        "user_id": "user123",
        "feature": "document_summarization"
    }
)
```

Operation names: `"chat"`, `"text_completion"`, `"embeddings"`, `"generate_content"`, `"create_agent"`, `"invoke_agent"`, `"execute_tool"`

### Track tenant ID

Set at request entry point:

```python
from cloud_sdk_python.core.telemetry import set_tenant_id

def handle_request(request):
    tenant_id = extract_tenant_from_jwt(request)
    set_tenant_id(tenant_id)
```

Thread-safe and async-safe. Automatic Propagation.

### Access current span

```python
from cloud_sdk_python.core.telemetry import get_current_span, add_span_attribute

span = get_current_span()
if span.is_recording():
    span.set_attribute("custom.key", "value")

# Or use the helper
add_span_attribute("request.id", request_id)
```

## Configuration

### Production (SAP BTP Managed Runtime)

No configuration needed. `OTEL_EXPORTER_OTLP_ENDPOINT` is automatically injected.

### Local Development

Set the OpenTelemetry collector endpoint:

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
from cloud_sdk_python.core.telemetry import (
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
