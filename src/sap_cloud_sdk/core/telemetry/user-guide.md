# Telemetry User Guide

## How it works

Telemetry has two layers that work together:

- **Auto-instrumentation** handles the *what*: LLM calls, token counts, latency, model names — automatically at startup.
- **Custom spans** handle the *who* and *why*: which agent, which user, which operation — context that autoinstrumentation can't infer.

The primary pattern is to wrap autoinstrumented calls in a parent span that carries your business context:

```
invoke_agent span  ← you create this (agent name, tenant, session, operation type)
  └─ chat span     ← autoinstrumentation creates this (model, tokens, latency)
```

Telemetry is initialized by calling `_instrument()` once at startup, before importing any AI libraries.

---

## Quick start

Call `_instrument()` once before importing AI libraries:

```python
from sap_cloud_sdk.core.telemetry._instrument import _instrument

_instrument()

from litellm import completion
# LLM calls are now automatically traced
```

For scripts or background workers with no web framework this is all that's needed. When used inside a web app, pass the app instance so framework instrumentors can hook in correctly:

```python
_instrument(app=app)
```

---

## Library instrumentation

At startup, the SDK automatically instruments any supported library that is already installed in the service — no extra configuration needed. If a library is not installed, it is silently skipped.

**Supported libraries:**

| Library      | What is traced                           |
|--------------|------------------------------------------|
| `httpx`      | Outbound HTTP requests (sync and async)  |
| `requests`   | Outbound HTTP requests                   |
| `grpcio`     | gRPC client and server calls             |
| `starlette`  | Inbound HTTP requests                    |
| `fastapi`    | Inbound HTTP requests with route details |
| `aiohttp`    | Outbound async HTTP requests             |
| `django`     | Inbound HTTP requests                    |
| `flask`      | Inbound HTTP requests                    |
| `sqlalchemy` | Database queries                         |
| `logging`    | Injects `trace_id` and `span_id` into every log record for log-trace correlation |

Instrumentation activates based on what is installed in the service, not on what extras were used to install the SDK. If your service has `django` in its own requirements, the SDK will instrument it automatically.

The SDK ships `opentelemetry-instrumentation-*` packages for all of the above as hard dependencies. The target frameworks themselves are optional — install them via your service's own requirements or via the SDK's convenience extras (e.g. `sap-cloud-sdk[django]`).

---

## Tenant and user attributes on spans

When the SDK is wired into a Starlette/FastAPI app, it automatically extracts the IAS JWT from the `Authorization` header and the trigger type from `x-sap-origin` on each request. These are stamped as span attributes on every span in that request:

- `sap.tenancy.tenant_id` from the `sap_gtid` claim
- `user.id` from the `user_uuid` claim
- `sap.ai.agent.trigger.type` from the `x-sap-origin` header

No extra configuration needed.

---

## Span functions

Add business context with a parent span that wraps your LLM calls:

```python
from sap_cloud_sdk.core.telemetry import invoke_agent_span

with invoke_agent_span(
    provider="openai", agent_name="SupportBot", conversation_id="conv-123"
):
    # autoinstrumented LLM call is a child of this span
    response = client.chat.completions.create(...)
```

For operations following [OpenTelemetry GenAI conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/):

```python
from sap_cloud_sdk.core.telemetry import chat_span, execute_tool_span, invoke_agent_span

# Agent invocation — top-level parent span for an agent turn
with invoke_agent_span(
    provider="openai", agent_name="SupportBot", conversation_id="cid"
):
    response = client.beta.threads.runs.create(...)

# LLM chat call — use when autoinstrumentation is not available
with chat_span(model="gpt-4", provider="openai", conversation_id="cid") as span:
    response = client.chat.completions.create(...)

# Tool execution
with execute_tool_span(
    tool_name="get_weather", tool_type="mcp", tool_description="weather mcp server"
):
    result = call_weather_api(location)
```

### Generic spans

Use `context_overlay` for operations without a dedicated function:

```python
from sap_cloud_sdk.core.telemetry import context_overlay, GenAIOperation

with context_overlay(GenAIOperation.RETRIEVAL, attributes={"index": "knowledge-base"}):
    documents = retrieve_documents(query)
```

Thread-safe and async-safe. Automatic Propagation.

### Propagate extension context

When calling extension tools (e.g., MCP servers), wrap the call in
`extension_context()` to propagate extension metadata via OTel baggage:

```python
from sap_cloud_sdk.core.telemetry import (
    extension_context,
    ExtensionType,
)

# When calling an extension tool
with extension_context(
    capability_id="default",
    extension_name="ServiceNow Extension",
):
    result = await mcp_client.call_tool("generate_offer_letter", args)
    # HTTP request includes baggage header with extension metadata
```

Available extension types:

```python
ExtensionType.TOOL  # MCP tool call (default)
ExtensionType.INSTRUCTION  # Instruction/prompt injection
```

In downstream services, read the propagated context:

```python
from sap_cloud_sdk.core.telemetry import get_extension_context

ext_ctx = get_extension_context()
if ext_ctx:
    print(ext_ctx["capability_id"])  # "default"
    print(ext_ctx["extension_name"])  # "ServiceNow Extension"
    print(ext_ctx["extension_type"])  # "tool"
```

The extension baggage span processor stamps `sap.extension.*` attributes on all spans created inside an `extension_context()` block, including spans from third-party instrumentation. It uses a built-in `BaggageSpanProcessor` under the hood to stamp baggage keys.

### Available operations

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
    propagate=True,
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
    invoke_agent_span,
    add_span_attribute,
)

from litellm import completion


async def handle_request(query: str, user_id: str):
    # tenant_id and user.id are stamped automatically from the IAS JWT
    with invoke_agent_span(
        provider="openai", agent_name="SupportBot", attributes={"user.id": user_id}
    ):
        documents = await retrieve_knowledge_base(query)
        add_span_attribute("documents.retrieved", len(documents))

        response = completion(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"Context: {documents}"},
                {"role": "user", "content": query},
            ],
        )

        return response
```

---

## Multi-tenancy

- **Supported:** N/A
- **Authentication:** N/A
- **How to use:** This is an infrastructure module. Tenant and user identifiers are extracted automatically from the IAS JWT and attached to every span as `sap.tenancy.tenant_id` and `user.id`.
- **Further reading:** N/A

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

By default, the SDK uses `BatchSpanProcessor`, which exports spans asynchronously in a background thread and is recommended for production workloads. For short-lived scripts or tests where the process may exit before the batch is flushed, pass `disable_batch=True`:

```python
_instrument(disable_batch=True)
```

### System role

```bash
export APPFND_CONHOS_SYSTEM_ROLE="S4HC"
```

### Solution area

```bash
export SAP_SOLUTION_AREA="AFND"
```

### ORD document ID

```bash
export ORD_DOCUMENT_ID="sap.foo:ord-doc:v1"
```
