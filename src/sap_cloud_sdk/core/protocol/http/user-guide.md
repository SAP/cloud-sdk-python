# HTTP Client User Guide

A shared HTTP client with injectable authentication and rotation-resilient token
management. Used internally by Agent Memory, Destination, and other SDK modules.
Can also be used directly when you need authenticated HTTP access to a BTP service
that is not yet covered by a dedicated SDK module.

## Table of Contents

- [HTTP Client User Guide](#http-client-user-guide)
  - [Table of Contents](#table-of-contents)
  - [Import](#import)
  - [Quick Start](#quick-start)
  - [Core Concepts](#core-concepts)
    - [`HttpClient`](#httpclient)
    - [`XsuaaAuthProvider`](#xsuaaauthprovider)
    - [`AuthProvider`](#authprovider)
    - [`HttpMethod`](#httpmethod)
  - [Binding Rotation](#binding-rotation)
  - [Troubleshooting](#troubleshooting)
    - [`RuntimeError: Failed to obtain OAuth2 token`](#runtimeerror-failed-to-obtain-oauth2-token)

---

## Import

```python
from sap_cloud_sdk.core.protocol.http import (
    HttpClient,
    HttpMethod,
    AuthProvider,
    XsuaaAuthProvider,
)
```

---

## Quick Start

```python
from sap_cloud_sdk.core.protocol.http import HttpClient, HttpMethod, XsuaaAuthProvider
from sap_cloud_sdk.core.secret_resolver import ConfigFactory

# Build a factory that re-reads the binding on every token refresh
factory = ConfigFactory(
    module="my-service",
    instance="default",
    binding_cls=MyBindingData,
    extract=MyBindingData.to_config,
)

# Create an auth provider backed by the factory
auth = XsuaaAuthProvider(factory)

# Create the HTTP client
client = HttpClient(base_url="https://my-service.example.com", auth_provider=auth)

# Make requests — auth and rotation handling are transparent
response = client.request(HttpMethod.GET, "/v1/resource")
response.raise_for_status()
data = response.json()

# Per-tenant (subscriber) requests
response = client.request(
    HttpMethod.POST,
    "/v1/resource",
    tenant_subdomain="my-tenant",
    json={"key": "value"},
)

# No-auth mode (local development)
local_client = HttpClient(base_url="http://localhost:8080")
```

---

## Core Concepts

### `HttpClient`

The main entry point. Wraps an `AuthProvider` (or a plain `requests.Session` in no-auth mode) and adds a single-retry on `HTTP 401`.

```python
HttpClient(
    base_url: str,
    auth_provider: Optional[AuthProvider] = None,  # None = no-auth mode
    *,
    timeout: float = 30.0,
)
```

| Method                                                 | Description                             |
| ------------------------------------------------------ | --------------------------------------- |
| `request(method, path, *, tenant_subdomain, **kwargs)` | Execute request; retry once on 401      |
| `close()`                                              | Release all held sessions and resources |

`**kwargs` are forwarded verbatim to `requests.Session.request` (e.g. `json=`, `headers=`, `params=`).

---

### `XsuaaAuthProvider`

OAuth2 client-credentials provider for XSUAA. Maintains a per-tenant token cache with
expiry-aware eviction and rotation resilience.

```python
XsuaaAuthProvider(
    config_factory: Callable[[], Any],  # ConfigFactory or any callable returning credentials
    *,
    timeout: float = 30.0,
)
```

The `config_factory` must return an object with `token_url`, `client_id`, `client_secret`,
and `identityzone` attributes — both `AgentMemoryConfig` and `DestinationConfig` satisfy
this contract.

Token derivation for subscriber tenants: when `tenant_subdomain` is provided to
`get_session()`, the subscriber token URL is derived by replacing `identityzone` in
`token_url` with the tenant subdomain.

---

### `AuthProvider`

Abstract base class for custom authentication strategies. Implement this to plug in
a non-XSUAA auth mechanism.

```python
class MyAuthProvider(AuthProvider):
    def get_session(self, tenant_subdomain=None) -> requests.Session: ...
    def invalidate(self, tenant_subdomain=None) -> None: ...
    def invalidate_all(self) -> None: ...
    def close(self) -> None: ...
```

---

### `HttpMethod`

Enum of standard HTTP verbs. Accepted by `HttpClient.request()` alongside plain strings.

```python
class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
```

---

## Binding Rotation

When BTP rotates the service binding secrets (e.g., periodic credential rotation in
Kubernetes), the client automatically picks up the new credentials without requiring a
restart. No configuration is required.

Two complementary layers handle this:

| Layer         | Trigger                                  | Behaviour                                                                            |
| ------------- | ---------------------------------------- | ------------------------------------------------------------------------------------ |
| **Proactive** | Secret directory `mtime` changes on disk | Token cache is evicted immediately; new credentials are read before the next request |
| **Reactive**  | Service returns `HTTP 401`               | Stale token is evicted and the request is retried once with a freshly obtained token |

> **Note:** Proactive detection only works when the binding is mounted as a Kubernetes
> secret volume. For environment-variable backed configurations the reactive (401-retry)
> layer still applies.

---

## Troubleshooting

### `RuntimeError: Failed to obtain OAuth2 token`

The token endpoint rejected the request. Common causes:

- `client_id` or `client_secret` in the service binding is incorrect.
- `token_url` is unreachable from the current environment.
- The binding was rotated but the old `ConfigFactory` cache was not evicted (should not
  happen under normal use — the reactive 401-retry will recover automatically on the next
  real request).
