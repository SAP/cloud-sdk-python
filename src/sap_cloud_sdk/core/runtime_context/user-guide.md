# Runtime Context User Guide

## How it works

The runtime context lets SDK modules read caller-identity information (tenant,
user, trigger type) for the current execution — without knowing where that
information came from or what framework is running.

- **`bootstrap(app)`** wires the SDK into your framework once at startup.
- **Providers** extract context from the current invocation (HTTP request, gRPC call, Kubernetes event, etc.).
- **`get_context()`** lets any module read that context via typed keys.

```
bootstrap(app)
  └─ registers middleware on your framework
       └─ on each invocation: providers extract → RuntimeContext set in ContextVar
            └─ anywhere: get_context().get(TENANT_ID)
```

---

## Quick start

### 1. Bootstrap at app startup

```python
from starlette.applications import Starlette
from sap_cloud_sdk import bootstrap

app = Starlette(...)
bootstrap(app)
```

By default `bootstrap` registers `IASContextProvider` (reads IAS JWT),
`SAPTriggerContextProvider` (reads `x-sap-origin`), and `DWCContextProvider`
(reads `dwc-subdomain`, `dwc-tenant`, and `dwc-stage-configuration`).

### 2. Read context anywhere

```python
from sap_cloud_sdk.core.runtime_context import (
    get_context,
    TENANT_ID,
    USER_ID,
    TRIGGER_TYPE,
)

ctx = get_context()
ctx.get(TENANT_ID)  # -> "abc-123" or None
ctx.get(USER_ID)  # -> "user-uuid" or None
ctx.get(TRIGGER_TYPE)  # -> "ui5" or None
```

---

## Context keys

Values are stored and retrieved by typed `ContextKey` instances — not strings.
Each provider owns the keys it defines. Import keys from the provider that
defined them.

```python
# IAS-owned keys:
from sap_cloud_sdk.core.runtime_context import TENANT_ID, USER_ID, GLOBAL_TENANT_ID

# SDK-standard keys (not tied to any specific source):
from sap_cloud_sdk.core.runtime_context import TRIGGER_TYPE

# Define your own:
from sap_cloud_sdk.core.runtime_context import ContextKey

MY_KEY = ContextKey[str]("my_key")
```

Keys are identity-based — two `ContextKey("same_name")` instances are different
keys. Always import the key from the module that defined it.

---

## Providers

A provider extracts a `RuntimeContext` from a `RequestEnvelope` — a
framework-agnostic carrier of whatever signals were available at invocation time
(headers, body, metadata). The provider doesn't know which framework built the
envelope; the framework adapter doesn't know what the provider does with it.

This means providers are reusable across transports. An `IASContextProvider`
written for HTTP headers works identically if the same headers appear in gRPC
metadata or a message queue envelope — as long as the adapter populates
`RequestEnvelope.headers` consistently.

### Built-in providers

| Provider | Reads | Sets |
|---|---|---|
| `IASContextProvider` | `Authorization: Bearer <JWT>` | `TENANT_ID`, `USER_ID`, `GLOBAL_TENANT_ID` |
| `SAPTriggerContextProvider` | `x-sap-origin` | `TRIGGER_TYPE` |
| `DWCContextProvider` | `dwc-subdomain`, `dwc-tenant`, `dwc-stage-configuration` | `DWC_SUBDOMAIN`, `DWC_TENANT`, `FEATURE_TOGGLES` |

### Feature toggles

`DWCContextProvider` reads the `dwc-stage-configuration` header. The value is
base64-encoded JSON with the shape:

```json
{
  "features": [
    {"name": "MY_FEATURE", "enabled": true},
    {"name": "OTHER_FEATURE", "enabled": false}
  ]
}
```

Only features with `"enabled": true` are included. Use `is_feature_enabled(name)`
to check a toggle for the current request:

```python
from sap_cloud_sdk.core.runtime_context import is_feature_enabled


@app.route("/")
async def handler(request):
    if is_feature_enabled("my-feature"):
        ...
```

`is_feature_enabled` returns `False` when the header is absent or the toggle
name is not in the active list.

> **Common pitfall:** `is_feature_enabled` always returns `False` if `bootstrap(app)` was never
> called. Without it, no middleware is registered, the `dwc-stage-configuration` header is never
> parsed, and `get_context()` returns an empty context for every request. Make sure `bootstrap` is
> called once at app startup before the server starts accepting requests.

For direct access to the full list:

```python
from sap_cloud_sdk.core.runtime_context import FEATURE_TOGGLES, get_context

toggles = get_context().get(FEATURE_TOGGLES)  # List[str] | None
```

### Custom providers

```python
from sap_cloud_sdk.core.runtime_context import (
    ContextKey,
    ContextProvider,
    RuntimeContext,
    RequestEnvelope,
)

CORRELATION_ID = ContextKey[str]("correlation_id")


class CorrelationIdProvider(ContextProvider):
    def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
        value = envelope.headers.get("x-correlation-id")
        return RuntimeContext({CORRELATION_ID: value} if value else {})
```

Pass it to `bootstrap`:

```python
from sap_cloud_sdk.core.runtime_context import (
    IASContextProvider,
    SAPTriggerContextProvider,
    DWCContextProvider,
)

bootstrap(
    app,
    providers=[
        IASContextProvider(),
        SAPTriggerContextProvider(),
        DWCContextProvider(),
        CorrelationIdProvider(),
    ],
)
```

### Merging

When multiple providers are registered, their results are merged — first writer
wins per key. Providers that set different keys don't interfere with each other.

---

## Framework adapters

`bootstrap` auto-detects the framework from the `app` type via registered
`FrameworkAdapter` instances. Each adapter knows how to intercept invocations
for one framework and build a `RequestEnvelope` from whatever the framework
exposes. Adding support for a new framework or invocation source never requires
editing `bootstrap`.

### Currently supported

| Framework | Detected via |
|---|---|
| Starlette / FastAPI | `isinstance(app, Starlette)` |

### Adding a new framework or invocation source

```python
from sap_cloud_sdk.core.runtime_context import (
    Adapter,
    ContextProvider,
    FrameworkAdapter,
    register,
)


class FlaskContextAdapter(FrameworkAdapter):
    @property
    def name(self) -> Adapter:
        return "flask"

    def _matches(self, app) -> bool:
        from flask import Flask

        return isinstance(app, Flask)

    def attach(self, app, providers: list[ContextProvider]) -> None:
        from my_flask_middleware import FlaskContextMiddleware

        app.before_request(FlaskContextMiddleware(providers).handle)


register(FlaskContextAdapter())
```

---

## Introspection

Use `get_attached_adapters()` to check which framework adapters have been attached at runtime:

```python
from sap_cloud_sdk.core.runtime_context import Adapter, get_attached_adapters

get_attached_adapters()  # -> [Adapter.STARLETTE] after bootstrap(app), [] before
```

This is useful for modules that need to fail fast if their required framework was never bootstrapped:

```python
if Adapter.STARLETTE not in get_attached_adapters():
    raise RuntimeError(
        "This client requires Starlette to be bootstrapped. "
        "Call bootstrap(app) with your Starlette/FastAPI app."
    )
```

Returns an empty list if `bootstrap()` has not been called yet. Each entry corresponds to one successful `bootstrap(app)` call.

---

## Running the tests

```bash
uv run pytest tests/core/unit/runtime_context/
```
