"""In-memory LRU + TTL cache backend backed by cachetools."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from cachetools import TTLCache

from sap_cloud_sdk.cache._backend import CacheBackend

logger = logging.getLogger(__name__)


class _EvictingTTLCache(TTLCache):
    """TTLCache subclass that fires an optional callback on eviction."""

    def __init__(
        self,
        maxsize: int,
        ttl: float,
        on_evict: Callable[[str, str], None] | None,
    ) -> None:
        super().__init__(maxsize=maxsize, ttl=ttl)
        self._on_evict = on_evict

    def popitem(self) -> tuple[Any, Any]:
        key, value = super().popitem()
        if self._on_evict is not None:
            try:
                self._on_evict(str(key), "lru")
            except Exception:
                logger.debug("on_evict callback raised an exception", exc_info=True)
        return key, value


class InMemoryLRUBackend(CacheBackend):
    """Thread-safe in-memory LRU + TTL cache.

    Uses :class:`cachetools.TTLCache` under the hood. Each entry has an
    individual TTL supplied at write time. Least-recently-used entries are
    evicted when *max_size* is exceeded.

    Suitable for single-process (single-instance) deployments. For
    horizontally scaled deployments implement a custom
    :class:`~sap_cloud_sdk.cache._backend.CacheBackend` backed by a shared
    store (Redis, Memcached, etc.) and pass it via
    :class:`~sap_cloud_sdk.cache._config.CacheConfig`.

    Args:
        max_size: Maximum number of entries before LRU eviction.
        on_evict: Optional callback ``(key, reason) -> None``. *reason* is
            ``"lru"`` for capacity evictions or ``"manual"`` for explicit
            :meth:`delete` / :meth:`clear` calls. TTL expiry is handled
            transparently by cachetools and does not fire this callback.
    """

    def __init__(
        self,
        max_size: int = 1000,
        on_evict: Callable[[str, str], None] | None = None,
    ) -> None:
        # cachetools TTLCache requires a single TTL at construction time; we
        # work around this by storing (value, expires_at_monotonic) tuples and
        # setting a very large cache-level TTL so cachetools never expires
        # entries on its own. Expiry is enforced in get() by comparing
        # time.monotonic() against the stored deadline.
        self._cache: _EvictingTTLCache = _EvictingTTLCache(
            maxsize=max_size,
            ttl=86400 * 365,  # 1 year — expiry managed manually per-entry
            on_evict=on_evict,
        )
        self._on_evict = on_evict
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() >= expires_at:
                try:
                    del self._cache[key]
                except KeyError:
                    pass
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        expires_at = time.monotonic() + max(ttl_seconds, 1)
        with self._lock:
            self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            existed = self._cache.pop(key, None) is not None
        if existed and self._on_evict is not None:
            try:
                self._on_evict(key, "manual")
            except Exception:
                logger.debug("on_evict callback raised an exception", exc_info=True)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
