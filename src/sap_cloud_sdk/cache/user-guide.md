# Cache: User Guide

Provides a domain-agnostic, pluggable cache layer shared across all SAP Cloud SDK modules. Supports tenant, tenant-user, and provider isolation, configurable TTL and expiry buffers, LRU eviction, and custom backends for multi-instance deployments.

## Installation

```bash
uv add sap-cloud-sdk
```

No BTP service binding is required — the cache module is self-contained.

## Quick Start

By default every SDK client uses an in-process LRU cache with sensible defaults. No configuration is needed unless you want to tune it.

```python
from sap_cloud_sdk.cache import CacheConfig, configure_cache

configure_cache(
    CacheConfig(
        default_ttl_seconds=600,
        expiry_buffer_seconds=60,
        max_size=2000,
    )
)
```

Call `configure_cache()` **once at startup**, before any SDK client is created. Changes made after client construction have no effect on already-instantiated clients.

## Configuration Reference

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | `bool` | `True` | Master on/off switch. `False` turns all gets into misses and all sets into no-ops. |
| `isolation_strategy` | `IsolationStrategy \| None` | `None` | Override automatic isolation. `None` = auto-detect from context. |
| `default_ttl_seconds` | `int` | `300` | Fallback TTL when no natural TTL is available. |
| `expiry_buffer_seconds` | `int` | `30` | Subtracted from any TTL before storing, to pre-invalidate entries. |
| `max_size` | `int` | `1000` | Maximum entries in the built-in backend before LRU eviction. |
| `backend` | `CacheBackend \| None` | `None` | Custom backend. `None` uses the built-in `InMemoryLRUBackend`. |
| `on_evict` | `Callable[[str, str], None] \| None` | `None` | Callback fired on eviction. Arguments: `(key, reason)` where reason is `"lru"`, `"ttl"`, or `"manual"`. |

## Isolation Strategy

The cache automatically scopes keys to the current tenant (and optionally user) to prevent cross-tenant and cross-user cache hits. Tenant and user identity are read implicitly from the active [`RuntimeContext`](../core/runtime_context) — callers do not pass them explicitly.

| Strategy | Scope | When to use |
|---|---|---|
| `TENANT` | Per tenant | Data shared across all users of a tenant (configuration, metadata). Auto-selected when no user ID is present. |
| `TENANT_USER` | Per (tenant, user) pair | User-specific data. Auto-selected when a user ID is present in context. |
| `PROVIDER` | Service-wide (single shared namespace) | Data that is not tenant-specific, e.g. CSRF tokens or provider-level metadata. Ignores tenant and user context entirely. Key: `provider`. |

Override the strategy globally:

```python
from sap_cloud_sdk.cache import CacheConfig, IsolationStrategy, configure_cache

configure_cache(CacheConfig(isolation_strategy=IsolationStrategy.TENANT))
```

Downgrading from `TENANT_USER` to `TENANT` when a user ID is present logs a warning, as it risks cross-user contamination.

## Disabling the Cache Per Client

Pass a `CacheConfig(enabled=False)` when constructing a client to disable caching for that client only, without affecting the global configuration:

```python
from sap_cloud_sdk.destination import create_client
from sap_cloud_sdk.cache import CacheConfig

client = create_client(cache_config=CacheConfig(enabled=False))
```

## Eviction Callback

```python
import logging
from sap_cloud_sdk.cache import CacheConfig, configure_cache

logger = logging.getLogger(__name__)


def on_evict(key: str, reason: str) -> None:
    logger.info("cache evicted key=%s reason=%s", key, reason)


configure_cache(CacheConfig(on_evict=on_evict))
```

`reason` values:
- `"lru"` — evicted because `max_size` was exceeded
- `"ttl"` — evicted on access after the entry's TTL elapsed
- `"manual"` — removed by an explicit `evict()` or `reset()` call

## Custom Backend (Multi-Instance Deployments)

The built-in `InMemoryLRUBackend` is process-local. For horizontally scaled deployments implement `CacheBackend` and pass it via `CacheConfig`:

```python
from typing import Any

from sap_cloud_sdk.cache import CacheBackend, CacheConfig, configure_cache


class MyCacheBackend(CacheBackend):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...


configure_cache(CacheConfig(backend=MyCacheBackend()))
```

The backend interface has exactly four methods and no awareness of tenants, TTL policy, or domain types — all of that is handled by the SDK before keys reach your backend.

> **Redis and other distributed backends:** A built-in Redis backend is not yet available. The `CacheBackend` ABC is designed to support distributed backends, and first-party support is planned for a future release. Until then, implement `CacheBackend` against your store of choice as shown above.

## Integration Example

For a real, in-tree example of how the cache is used, see `XsuaaAuthProvider` in `sap_cloud_sdk.core.protocol.http.models`. It uses `IsolationStrategy.TENANT` to cache OAuth2 sessions per tenant, with TTL derived from the token's `expires_in` field and automatic eviction on secret rotation.

## API Reference

### `configure_cache(config: CacheConfig) -> None`

Sets the global cache configuration. Must be called before any SDK client is created.

### `get_cache_config() -> CacheConfig`

Returns the current global cache configuration.

### `class CacheConfig`

Dataclass holding all cache settings. See [Configuration Reference](#configuration-reference) above.

### `class CacheBackend` (ABC)

Abstract base for custom backends. Implement `get`, `set`, `delete`, and `clear`.

### `class InMemoryLRUBackend`

The default backend. Thread-safe, LRU + TTL eviction, backed by `cachetools.TTLCache`. Suitable for single-process deployments.

### `class IsolationStrategy`

Enum with values `TENANT`, `TENANT_USER`, and `PROVIDER`. See [Isolation Strategy](#isolation-strategy) above.

## Multi-tenancy

- **Supported:** Yes, `TENANT`, `TENANT_USER`, and `PROVIDER` isolation strategies
- **Authentication:** N/A, the cache module does not perform BTP authentication
- **How to use:** Set `isolation_strategy` in `CacheConfig`. Tenant and user identity are read implicitly from the active [`RuntimeContext`](../core/runtime_context); auto-selection uses `TENANT_USER` when a user ID is present in context, otherwise `TENANT`. Use `PROVIDER` for service-wide data that must not be tenant-scoped.
- **Further reading:** N/A

## Error Handling

```python
from sap_cloud_sdk.cache.exceptions import BackendError, CacheError

try:
    # SDK client operations that use the cache internally
    ...
except BackendError as e:
    # Raised when a custom backend raises during a set() call
    print(f"Cache backend error: {e}")
except CacheError as e:
    print(f"Cache error: {e}")
```

Cache misses and backend errors during `get()` are always safe — the SDK treats them as misses and falls back to a fresh fetch.
