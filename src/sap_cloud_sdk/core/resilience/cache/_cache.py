"""SDK-internal cache façade.

SDK modules instantiate ``Cache`` per-client and call its
``get``/``set``/``evict``/``reset`` methods. The façade handles:

- Selecting the active backend (per-client override or global default).
- Building namespaced, isolation-scoped keys.
- Applying the expiry buffer before forwarding TTLs to the backend.
- Honouring the ``enabled`` flag.

This class is **not part of the public API** and is not exported from
``sap_cloud_sdk.core.resilience.cache``. Import it directly:

    from sap_cloud_sdk.core.resilience.cache._cache import Cache
"""

from __future__ import annotations

import logging
from typing import Any

from sap_cloud_sdk.core.resilience.cache._backend import CacheBackend
from sap_cloud_sdk.core.resilience.cache._config import (
    CacheConfig,
    get_cache_config,
    is_cache_disabled_by_env,
)
from sap_cloud_sdk.core.resilience.cache._isolation import build_isolation_key
from sap_cloud_sdk.core.resilience.cache._lru_backend import InMemoryLRUBackend
from sap_cloud_sdk.core.resilience.cache._registry import get_module_backend
from sap_cloud_sdk.core.resilience.cache.exceptions import BackendError

logger = logging.getLogger(__name__)


class Cache:
    """Per-client cache façade.

    Tenant and user isolation keys are derived automatically from the active
    runtime context — callers do not need to pass identity information explicitly.

    Args:
        config: Per-client override. When ``None``, the global config set via
            ``configure_cache()`` is used. The config is snapshotted at
            construction time — subsequent calls to ``configure_cache()`` do
            not affect an existing ``Cache``.
        module: Optional logical module name (e.g. ``"agentgateway"``).
            When given, all ``Cache`` instances with the same *module* name
            share a single ``InMemoryLRUBackend`` that lives for the process
            lifetime. This lets modules that create a new client on every
            request still benefit from cross-request caching.

            ``max_size`` and ``on_evict`` are taken from the **first**
            ``Cache`` created for a given *module* name; later callers with
            different values are silently ignored. Pass ``None`` (the
            default) to get a per-instance cache backend — nothing is
            shared.

            An explicit ``CacheConfig(backend=...)`` always takes precedence
            over *module*.
    """

    def __init__(
        self,
        config: CacheConfig | None = None,
        *,
        module: str | None = None,
    ) -> None:
        self._config: CacheConfig = config if config is not None else get_cache_config()
        self._module: str | None = module
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
        if not self._is_enabled():
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
        if not self._is_enabled():
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
        if not self._is_enabled():
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

    def _is_enabled(self) -> bool:
        """Return whether reads and writes are active.

        The cache is active only when ``CacheConfig.enabled`` is ``True`` and the
        ``CLOUD_SDK_CACHE_DISABLED`` kill switch is not set. The env var is checked
        at call time and always wins, so ops can disable the cache without a
        redeploy even when application code hardcodes ``enabled=True``.
        """
        return self._config.enabled and not is_cache_disabled_by_env()

    def _resolve_backend(self) -> CacheBackend:
        # 1. Explicit backend wins (e.g. Redis)
        if self._config.backend is not None:
            return self._config.backend

        # 2. Per-module shared backend, memoized by name
        if self._module is not None:
            return get_module_backend(
                self._module,
                self._config.max_size,
                self._config.on_evict,
            )

        # 3. Fresh per-instance backend
        return InMemoryLRUBackend(
            max_size=self._config.max_size,
            on_evict=self._config.on_evict,
        )

    def _make_full_key(self, namespace: str, key: str) -> str:
        isolation_key = build_isolation_key(strategy=self._config.isolation_strategy)
        return f"{namespace}::{isolation_key}::{key}"
