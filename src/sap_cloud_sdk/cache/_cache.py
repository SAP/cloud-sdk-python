"""SDK-internal cache façade.

SDK modules instantiate :class:`Cache` per-client and call its
``get``/``set``/``evict``/``reset`` methods. The façade handles:

- Selecting the active backend (per-client override or global default).
- Building namespaced, isolation-scoped keys.
- Applying the expiry buffer before forwarding TTLs to the backend.
- Honouring the ``enabled`` flag.

This class is **not part of the public API** and is not exported from
``sap_cloud_sdk.cache``. Import it directly::

    from sap_cloud_sdk.cache._cache import Cache
"""

from __future__ import annotations

import logging
from typing import Any

from sap_cloud_sdk.cache._backend import CacheBackend
from sap_cloud_sdk.cache._config import CacheConfig, get_cache_config
from sap_cloud_sdk.cache._isolation import build_isolation_key
from sap_cloud_sdk.cache._lru_backend import InMemoryLRUBackend
from sap_cloud_sdk.cache.exceptions import BackendError

logger = logging.getLogger(__name__)


class Cache:
    """Per-client cache façade.

    Tenant and user isolation keys are derived automatically from the active
    :func:`~sap_cloud_sdk.core.runtime_context.get_context` — callers do not
    need to pass identity information explicitly.

    Args:
        config: Per-client override. When ``None``, the global config set via
            :func:`~sap_cloud_sdk.cache._config.configure_cache` is used.
            The config is snapshotted at construction time — subsequent calls
            to :func:`configure_cache` do not affect an existing ``Cache``.
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        self._config: CacheConfig = config if config is not None else get_cache_config()
        self._backend = self._resolve_backend()

    # ------------------------------------------------------------------
    # Public façade methods
    # ------------------------------------------------------------------

    def get(self, namespace: str, key: str) -> Any | None:
        """Return a cached value, or ``None`` on miss or when disabled.

        Args:
            namespace: Domain namespace, e.g. ``"csrf"``.
            key: Domain-specific key, e.g. the service root URL.
        """
        if not self._config.enabled:
            return None

        full_key = self._make_full_key(namespace, key)
        try:
            return self._backend.get(full_key)
        except Exception as e:
            logger.warning("cache backend get() raised an exception: %s", e)
            return None

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: int | None,
    ) -> None:
        """Store a value in the cache.

        The effective TTL forwarded to the backend is:
        - *ttl_seconds* − ``expiry_buffer_seconds`` when *ttl_seconds* is given.
        - ``default_ttl_seconds`` − ``expiry_buffer_seconds`` as fallback.

        The result is clamped to a minimum of 1 second.

        Args:
            namespace: Domain namespace.
            key: Domain-specific key.
            value: Value to cache (must be serialisable by the backend).
            ttl_seconds: Natural TTL derived from the resource (e.g. token
                ``exp`` minus now). Pass ``None`` to use the configured
                default.
        """
        if not self._config.enabled:
            return

        raw_ttl = (
            ttl_seconds if ttl_seconds is not None else self._config.default_ttl_seconds
        )
        effective_ttl = max(raw_ttl - self._config.expiry_buffer_seconds, 1)

        full_key = self._make_full_key(namespace, key)
        try:
            self._backend.set(full_key, value, effective_ttl)
        except Exception as e:
            raise BackendError(f"cache backend set() failed: {e}") from e

    def evict(self, namespace: str, key: str) -> None:
        """Remove a single entry (no-op if absent or cache is disabled).

        Args:
            namespace: Domain namespace.
            key: Domain-specific key.
        """
        if not self._config.enabled:
            return

        full_key = self._make_full_key(namespace, key)
        try:
            self._backend.delete(full_key)
        except Exception as e:
            logger.warning("cache backend delete() raised an exception: %s", e)

    def reset(self) -> None:
        """Clear all entries from the backend.

        Use with care in production — this forces a full re-fetch of every
        cached resource on the next access.
        """
        try:
            self._backend.clear()
        except Exception as e:
            logger.warning("cache backend clear() raised an exception: %s", e)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_backend(self) -> CacheBackend:
        if self._config.backend is not None:
            return self._config.backend
        return InMemoryLRUBackend(
            max_size=self._config.max_size,
            on_evict=self._config.on_evict,
        )

    def _make_full_key(self, namespace: str, key: str) -> str:
        isolation_key = build_isolation_key(strategy=self._config.isolation_strategy)
        return f"{namespace}::{isolation_key}::{key}"
