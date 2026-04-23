# Telemetry User Guide

## How it works

Telemetry has two layers that work together:

- **Auto-instrumentation** handles the *what*: LLM calls, token counts, latency, model names — automatically, by calling auto_instrument() once.
- **Custom spans** handle the *who* and *why*: which agent, which user, which operation — context that autoinstrumentation can't infer.

The primary pattern is to wrap autoinstrumented calls in a parent span that carries your business context:

```
invoke_agent span  ← you create this (agent name, tenant, session, operation type)
  └─ chat span     ← autoinstrumentation creates this (model, tokens, latency)
```

## Quick start

### 1. Enable auto-instrumentation

Call before importing AI libraries:

```python
from sap_cloud_sdk.core.telemetry import auto_instrument

auto_instrument()

from litellm import completion
# LLM calls are now automatically traced
```

### 2. Add business context with a parent span

Wrap your LLM calls to add the context autoinstrumentation can't provide:

```python
from sap_cloud_sdk.core.telemetry import invoke_agent_span

with invoke_agent_span(provider="openai", agent_name="SupportBot", conversation_id="conv-123"):
    # autoinstrumented LLM call is a child of this span
    response = client.chat.completions.create(...)
```

### 3. Set tenant ID at the request boundary

```python
from sap_cloud_sdk.core.telemetry import set_tenant_id

def handle_request(request):
    set_tenant_id(extract_tenant_from_jwt(request))
```

---

## Span functions

For operations following [OpenTelemetry GenAI conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/):

```python
from sap_cloud_sdk.core.telemetry import chat_span, execute_tool_span, invoke_agent_span

# Agent invocation — top-level parent span for an agent turn
with invoke_agent_span(provider="openai", agent_name="SupportBot", conversation_id="cid"):
    response = client.beta.threads.runs.create(...)

# LLM chat call — use when autoinstrumentation is not available
with chat_span(model="gpt-4", provider="openai", conversation_id="cid") as span:
    response = client.chat.completions.create(...)

# Tool execution
with execute_tool_span(tool_name="get_weather", tool_type="mcp", tool_description="weather mcp server"):
    result = call_weather_api(location)
```

### Generic spans

Use `context_overlay` for operations without a dedicated function:

```python
from sap_cloud_sdk.core.telemetry import context_overlay, GenAIOperation

with context_overlay(GenAIOperation.RETRIEVAL, attributes={"index": "knowledge-base"}):
    documents = retrieve_documents(query)
```

Available operations:

```python
GenAIOperation.CHAT
GenAIOperation.TEXT_COMPLETION
GenAIOperation.EMBEDDINGS
GenAIOperation.GENERATE_CONTENT
GenAIOperation.RETRIEVAL
GenAIOperation.EXECUTE_TOOL
GenAIOperation.CREATE_AGENT
GenAIOperation.INVOKE_AGENT
```

---

## Adding attributes

### To the current span

Add attributes to whichever span is currently active — including autoinstrumented ones:

```python
from sap_cloud_sdk.core.telemetry import add_span_attribute

with invoke_agent_span(provider="openai", agent_name="SupportBot"):
    response = client.chat.completions.create(...)
    add_span_attribute("response.length", len(response.choices[0].message.content))
```

### To a specific span

Every span function yields the span for direct access:

```python
with invoke_agent_span(provider="openai", agent_name="SupportBot") as span:
    span.add_event("tool_selected", attributes={"tool": "search"})
    response = client.chat.completions.create(...)
```

### Propagating parent attributes to child spans

By default, attributes set on a parent span stay on that span. If you need attributes to also appear on child spans — for example, to filter by `user.id` at the LLM span level in your observability backend — use `propagate=True`:

```python
with invoke_agent_span(
    provider="openai",
    agent_name="SupportBot",
    attributes={"user.id": "u-456"},
    propagate=True
):
    # child spans automatically receive user.id
    with execute_tool_span("search"):
        ...
    with chat_span("gpt-4", "openai"):
        ...
```

> **Note:** `propagate=True` is specific for backends that require attributes to appear on every span individually. In most cases, querying by the parent span is sufficient and preferred.

**Priority rules** — child span values always win (highest to lowest):
1. Required semantic keys set by the span function (e.g. `gen_ai.operation.name`)
2. User-provided `attributes` on the child span
3. Propagated attributes from ancestors

Propagation is scoped: once the parent span exits, its attributes stop propagating to subsequent spans.

---

## Complete example

```python
from sap_cloud_sdk.core.telemetry import (
    auto_instrument,
    invoke_agent_span,
    execute_tool_span,
    set_tenant_id,
    add_span_attribute,
)

auto_instrument()

from litellm import completion

async def handle_request(query: str, user_id: str):
    set_tenant_id("bh7sjh...")

    # Parent span carries business context for the whole agent turn.
    # Autoinstrumentation creates the child LLM span automatically.
    with invoke_agent_span(
        provider="openai",
        agent_name="SupportBot",
        attributes={"user.id": user_id}
    ):
        documents = await retrieve_knowledge_base(query)
        add_span_attribute("documents.retrieved", len(documents))

        response = completion(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"Context: {documents}"},
                {"role": "user", "content": query}
            ]
        )

        return response
```

## Configuration

### Production

Ensure `OTEL_EXPORTER_OTLP_ENDPOINT` points to your OTLP endpoint.

### Local development

Print traces to console:

```bash
export OTEL_TRACES_EXPORTER=console
```

Use an OTLP collector:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otel-collector.example.com"
```

### Transport protocol

Both traces and metrics use gRPC by default. Switch to HTTP/protobuf by setting:

```bash
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
```

Supported values: `grpc` (default), `http/protobuf`.

### Span processor

By default, `auto_instrument` uses `BatchSpanProcessor`, which exports spans asynchronously in a background thread and is recommended for production workloads. If you need synchronous span processing (e.g. in short-lived scripts or tests where the process may exit before the batch is flushed), pass `disable_batch=True`:

```python
auto_instrument(disable_batch=True)
```

### System role

```bash
export APPFND_CONHOS_SYSTEM_ROLE="S4HC"
```

### Solution area

```bash
export SAP_SOLUTION_AREA="AFND"
```
