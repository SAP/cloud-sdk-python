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

By default `bootstrap` registers `IASContextProvider` (reads IAS JWT) and
`HeaderContextProvider` (reads SAP standard headers like `x-sap-origin`).

### 2. Read context anywhere

```python
from sap_cloud_sdk.core.runtime_context import get_context, TENANT_ID, USER_ID, TRIGGER_TYPE

ctx = get_context()
ctx.get(TENANT_ID)    # -> "abc-123" or None
ctx.get(USER_ID)      # -> "user-uuid" or None
ctx.get(TRIGGER_TYPE) # -> "ui5" or None
```

---

## Context keys

Values are stored and retrieved by typed `ContextKey` instances — not strings.
Each provider owns the keys it defines. Import keys from the provider that
defined them.

```python
# IAS-owned keys:
from sap_cloud_sdk.core.runtime_context import TENANT_ID, USER_ID, IAS_CLAIMS

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
| `IASContextProvider` | `Authorization: Bearer <JWT>` | `TENANT_ID`, `USER_ID`, `IAS_CLAIMS` |
| `HeaderContextProvider` | `x-sap-origin` | `TRIGGER_TYPE` |

### Custom providers

```python
from sap_cloud_sdk.core.runtime_context import (
    ContextKey, ContextProvider, RuntimeContext, RequestEnvelope
)

CORRELATION_ID = ContextKey[str]("correlation_id")

class CorrelationIdProvider(ContextProvider):
    def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
        value = envelope.headers.get("x-correlation-id")
        return RuntimeContext({CORRELATION_ID: value} if value else {})
```

Pass it to `bootstrap`:

```python
from sap_cloud_sdk.core.runtime_context import IASContextProvider, HeaderContextProvider

bootstrap(app, providers=[IASContextProvider(), HeaderContextProvider(), CorrelationIdProvider()])
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
from sap_cloud_sdk.core.runtime_context import ContextProvider, FrameworkAdapter, register

class FlaskContextAdapter(FrameworkAdapter):
    def _matches(self, app) -> bool:
        from flask import Flask
        return isinstance(app, Flask)

    def attach(self, app, providers: list[ContextProvider]) -> None:
        from my_flask_middleware import FlaskContextMiddleware
        app.before_request(FlaskContextMiddleware(providers).handle)

register(FlaskContextAdapter())
```

---

## Manual usage (tests, CLI, scripts)

When there is no framework to bootstrap — unit tests, CLI tools, background
jobs — set the context directly for the duration of a block:

```python
from sap_cloud_sdk.core.runtime_context import sdk_context, RuntimeContext, TENANT_ID, USER_ID

# Sync:
with sdk_context(RuntimeContext({TENANT_ID: "test-tenant", USER_ID: "test-user"})):
    result = some_sdk_call()

# Async:
from sap_cloud_sdk.core.runtime_context import async_sdk_context

async with async_sdk_context(RuntimeContext({TENANT_ID: "test-tenant"})):
    result = await some_async_sdk_call()
```

---

## Running the tests

```bash
uv run pytest tests/core/unit/runtime_context/
```
