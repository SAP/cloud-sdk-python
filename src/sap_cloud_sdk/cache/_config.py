"""Global cache configuration and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sap_cloud_sdk.cache._backend import CacheBackend
    from sap_cloud_sdk.cache._isolation import IsolationStrategy


@dataclass
class CacheConfig:
    """Configuration for the SDK cache layer.

    Can be set globally via :func:`configure_cache` or passed per-client
    to override the global for that client only.

    Attributes:
        enabled: Master on/off switch. When ``False``, all gets return
            ``None`` and all sets are no-ops.
        isolation_strategy: Override the automatic isolation selection.
            ``None`` means auto-detect from context (``TENANT_USER`` when a
            user ID is present, ``TENANT`` otherwise).
        default_ttl_seconds: Fallback TTL used when the caller does not
            supply a natural TTL (e.g. from a token ``exp`` claim).
        expiry_buffer_seconds: Seconds subtracted from any derived TTL to
            pre-invalidate entries before they expire on the remote service.
        max_size: Maximum number of entries in the built-in in-memory
            backend before LRU eviction kicks in.
        backend: Custom cache backend. ``None`` uses the built-in
            :class:`~sap_cloud_sdk.cache._lru_backend.InMemoryLRUBackend`.
        on_evict: Optional callback invoked when an entry is evicted.
            Signature: ``(key: str, reason: str) -> None`` where *reason*
            is one of ``"ttl"``, ``"lru"``, or ``"manual"``.
    """

    enabled: bool = True
    isolation_strategy: IsolationStrategy | None = None
    default_ttl_seconds: int = 300
    expiry_buffer_seconds: int = 30
    max_size: int = 1000
    backend: CacheBackend | None = None
    on_evict: Callable[[str, str], None] | None = field(default=None, repr=False)


_global_config: CacheConfig = CacheConfig()


def configure_cache(config: CacheConfig) -> None:
    """Set the global cache configuration.

    Must be called before any SDK client is created. Hot-reload is not
    supported — changes after clients are constructed have no effect on
    already-instantiated :class:`~sap_cloud_sdk.cache._cache.Cache` objects.

    Args:
        config: The new global configuration.
    """
    global _global_config
    _global_config = config


def get_cache_config() -> CacheConfig:
    """Return the current global cache configuration."""
    return _global_config
