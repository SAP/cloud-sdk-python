"""Pluggable token cache for any SDK module that fetches OAuth2 tokens.

Provides:
- :class:`TokenCache` — abstract protocol; plug in any backend.
- :class:`InMemoryTokenCache` — default, single-process (thread-safe dict).
- :class:`RedisTokenCache` — shared cache for multi-instance / Kyma deployments.

Usage::

    # Single instance (default)
    from sap_cloud_sdk.core.auth import IasTokenFetcher, InMemoryTokenCache
    fetcher = IasTokenFetcher(ias_url=..., client_id=..., client_secret=...)

    # Multi-instance: share tokens via Redis
    from sap_cloud_sdk.core.auth import IasTokenFetcher, RedisTokenCache
    cache = RedisTokenCache(host="redis-host", ssl=True)
    fetcher = IasTokenFetcher(ias_url=..., client_id=..., client_secret=..., cache=cache)
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from typing import Optional


class TokenCache(ABC):
    """Abstract token cache interface.

    Implement this to plug in any cache backend (Redis, Memcached, DB, etc.).
    All SDK authentication modules accept a ``TokenCache`` instance so the
    same backend can be shared across multiple service clients.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Return a cached access token for *key*, or ``None`` if missing / expired."""

    @abstractmethod
    def set(self, key: str, token: str, ttl_seconds: int) -> None:
        """Store *token* under *key* with a time-to-live in seconds."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Invalidate a cached token (e.g. after a 401 response)."""


class InMemoryTokenCache(TokenCache):
    """Thread-safe in-memory token cache.

    Suitable for single-process (single-instance) deployments.
    For multi-instance deployments (Kyma, Cloud Foundry with ``instances > 1``)
    use :class:`RedisTokenCache` to share tokens across pods.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}  # key → (token, expires_at)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            token, expires_at = entry
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None
            return token

    def set(self, key: str, token: str, ttl_seconds: int) -> None:
        with self._lock:
            self._store[key] = (token, time.monotonic() + ttl_seconds)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)


class RedisTokenCache(TokenCache):
    """Shared token cache backed by Redis.

    Use this for multi-instance deployments (Kyma / Cloud Foundry ``instances: 2+``)
    to prevent each pod from fetching its own independent token and causing
    unnecessary load on the IAS / XSUAA token endpoint.

    Requires the ``redis`` package::

        pip install redis

    Args:
        host: Redis hostname.
        port: Redis port (default 6379).
        db: Redis database index (default 0).
        password: Redis AUTH password (optional).
        ssl: Enable TLS connection (default ``True`` — matches SAP Redis BTP service).
        key_prefix: Namespace prefix for all cache keys (default ``"sap_sdk:tokens:"``).
        socket_timeout: Connection timeout in seconds (default 5).

    Example::

        from sap_cloud_sdk.core.auth import RedisTokenCache, IasTokenFetcher
        cache = RedisTokenCache(
            host="adm-redis.redis.svc.cluster.local",
            ssl=True,
            password="<redis-auth>",
        )
        fetcher = IasTokenFetcher(
            ias_url="https://tenant.accounts.ondemand.com",
            client_id="...",
            client_secret="...",
            cache=cache,
        )
    """

    _DEFAULT_PREFIX = "sap_sdk:tokens:"

    def __init__(
        self,
        host: str,
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = True,
        key_prefix: str = _DEFAULT_PREFIX,
        socket_timeout: int = 5,
    ) -> None:
        try:
            import redis  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "RedisTokenCache requires the 'redis' package. "
                "Install it with: pip install redis"
            ) from exc

        self._prefix = key_prefix
        self._r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=ssl,
            socket_timeout=socket_timeout,
            decode_responses=True,
        )

    def get(self, key: str) -> Optional[str]:
        try:
            return self._r.get(self._prefix + key)
        except Exception:
            # On Redis failure, fall through to a fresh token fetch
            return None

    def set(self, key: str, token: str, ttl_seconds: int) -> None:
        try:
            self._r.setex(self._prefix + key, ttl_seconds, token)
        except Exception:
            pass  # Cache write failure is non-fatal

    def delete(self, key: str) -> None:
        try:
            self._r.delete(self._prefix + key)
        except Exception:
            pass
