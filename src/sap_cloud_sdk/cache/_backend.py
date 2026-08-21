"""Abstract cache backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CacheBackend(ABC):
    """Domain-agnostic key/value cache backend.

    The backend has no awareness of tenants, TTL policy, namespaces, or domain
    types. All of that is handled by the :class:`~sap_cloud_sdk.cache._cache.Cache`
    façade before keys and values reach the backend.

    Implement this to plug in any shared cache (Redis, Memcached, etc.) for
    multi-instance deployments (Kyma ``replicas > 1``, Cloud Foundry
    ``instances > 1``).
    """

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return the value for *key*, or ``None`` if absent or expired."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store *value* under *key* with a time-to-live in seconds."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the entry for *key* (no-op if absent)."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries."""
