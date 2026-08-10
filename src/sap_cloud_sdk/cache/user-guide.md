# Cache: User Guide

Provides a domain-agnostic, pluggable cache layer shared across all SAP Cloud SDK modules. Supports tenant and tenant-user isolation, configurable TTL and expiry buffers, LRU eviction, and custom backends for multi-instance deployments.

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
| `on_evict` | `Callable[[str, str], None] \| None` | `None` | Callback fired on eviction. Arguments: `(key, reason)` where reason is `"lru"` or `"manual"`. |

## Isolation Strategy

The cache automatically scopes keys to the current tenant (and optionally user) to prevent cross-tenant and cross-user cache hits.

| Strategy | Scope | Auto-selected when |
|---|---|---|
| `TENANT` | Per tenant | No user ID present |
| `TENANT_USER` | Per (tenant, user) pair | User ID is present |

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
- `"manual"` — removed by an explicit `evict()` or `reset()` call

## Custom Backend (Multi-Instance Deployments)

The built-in `InMemoryLRUBackend` is process-local. For horizontally scaled deployments implement `CacheBackend` and pass it via `CacheConfig`:

```python
from sap_cloud_sdk.cache import CacheBackend, CacheConfig, configure_cache


class MyCacheBackend(CacheBackend):
    def get(self, key: str): ...
    def set(self, key: str, value, ttl_seconds: int) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...


configure_cache(CacheConfig(backend=MyCacheBackend()))
```

The backend interface has exactly four methods and no awareness of tenants, TTL policy, or domain types — all of that is handled by the SDK before keys reach your backend.

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

Enum with values `TENANT` and `TENANT_USER`. See [Isolation Strategy](#isolation-strategy) above.

## Multi-tenancy

- **Supported:** Yes, `TENANT` and `TENANT_USER` isolation strategies
- **Authentication:** N/A, the cache module does not perform BTP authentication
- **How to use:** Set `isolation_strategy` in `CacheConfig`. Auto-selection uses `TENANT_USER` when a `user_id` is provided to `Cache.get()`/`Cache.set()`, otherwise `TENANT`
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
