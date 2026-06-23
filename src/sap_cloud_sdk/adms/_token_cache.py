"""Pluggable token cache for any SDK module that fetches OAuth2 tokens.

Provides:
- :class:`TokenCache` — abstract protocol; plug in any backend.
- :class:`InMemoryTokenCache` — default, single-process (thread-safe dict).

Usage::

    from sap_cloud_sdk.adms import IasTokenFetcher, InMemoryTokenCache
    fetcher = IasTokenFetcher(ias_url=..., client_id=..., client_secret=...)

For multi-instance deployments (Kyma ``replicas > 1``, Cloud Foundry
``instances > 1``) where you need to share tokens across pods, implement a
custom :class:`TokenCache` subclass backed by your runtime's shared cache
(e.g. Redis, Memcached, hyperscaler key-value store) and pass it via the
``cache=`` argument.
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

    Suitable for single-process (single-instance) deployments.  For
    horizontally scaled deployments (Kyma ``replicas > 1``, Cloud Foundry
    ``instances > 1``) implement a :class:`TokenCache` subclass that delegates
    to your runtime's shared cache backend.
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
