"""SAP Cloud SDK for Python - Cache module.

Provides a domain-agnostic, pluggable cache layer shared across all SDK
modules. Supports tenant and tenant-user isolation, configurable TTL and
expiry buffers, LRU eviction, and custom backends for multi-instance
deployments.

Global configuration example::

    from sap_cloud_sdk.cache import CacheConfig, configure_cache

    configure_cache(CacheConfig(
        default_ttl_seconds=600,
        expiry_buffer_seconds=60,
        max_size=2000,
    ))

Disabling the cache for a specific client::

    from sap_cloud_sdk.destination import create_client
    from sap_cloud_sdk.cache import CacheConfig

    client = create_client(cache_config=CacheConfig(enabled=False))

Custom backend example (Redis)::

    from sap_cloud_sdk.cache import CacheBackend, CacheConfig, configure_cache

    class RedisCacheBackend(CacheBackend):
        def get(self, key): ...
        def set(self, key, value, ttl_seconds): ...
        def delete(self, key): ...
        def clear(self): ...

    configure_cache(CacheConfig(backend=RedisCacheBackend(...)))
"""

from sap_cloud_sdk.cache._backend import CacheBackend
from sap_cloud_sdk.cache._config import CacheConfig, configure_cache, get_cache_config
from sap_cloud_sdk.cache._isolation import IsolationStrategy
from sap_cloud_sdk.cache._lru_backend import InMemoryLRUBackend
from sap_cloud_sdk.cache.exceptions import BackendError, CacheError

__all__ = [
    "CacheBackend",
    "CacheConfig",
    "configure_cache",
    "get_cache_config",
    "IsolationStrategy",
    "InMemoryLRUBackend",
    "CacheError",
    "BackendError",
]
