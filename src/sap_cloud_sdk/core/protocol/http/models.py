"""HTTP authentication providers and method enum."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Optional

import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from sap_cloud_sdk.cache._cache import Cache
from sap_cloud_sdk.cache._config import CacheConfig
from sap_cloud_sdk.cache._isolation import IsolationStrategy
from sap_cloud_sdk.core._tenant import (
    _derive_tenant_token_url,
    _validate_tenant_subdomain,
)

logger = logging.getLogger(__name__)

_TOKEN_EXPIRY_BUFFER_SECONDS = 60
_DEFAULT_TIMEOUT = 30.0
_TOKEN_NAMESPACE = "xsuaa_token"


class HttpMethod(Enum):
    """Standard HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class AuthProvider(ABC):
    """Abstract authentication provider."""

    @abstractmethod
    def get_session(self, tenant_subdomain: Optional[str] = None) -> requests.Session:
        """Return a session ready to make authenticated requests."""

    @abstractmethod
    def invalidate(self, tenant_subdomain: Optional[str] = None) -> None:
        """Evict the cached token for the given tenant."""

    @abstractmethod
    def invalidate_all(self) -> None:
        """Evict all cached tokens."""

    @abstractmethod
    def close(self) -> None:
        """Release all held resources."""


class XsuaaAuthProvider(AuthProvider):
    """OAuth2 client-credentials auth provider for XSUAA.

    Caches tokens per tenant subdomain with expiry-aware eviction backed by the
    SDK :class:`~sap_cloud_sdk.cache._cache.Cache` module.
    Re-reads credentials from the binding on every token refresh so that
    rotated secrets are picked up automatically.
    Detects rotation proactively by checking the secret directory mtime before
    each cache hit via :meth:`~ConfigFactory.has_changed`.

    Args:
        config_factory: A :class:`~sap_cloud_sdk.core.secret_resolver.ConfigFactory`
            (or any callable with a ``has_changed() -> bool`` method) that returns
            fresh XSUAA credentials on every call.
        timeout: Timeout in seconds for token-endpoint requests.
    """

    def __init__(
        self,
        config_factory: Callable[[], Any],
        *,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._config_factory = config_factory
        self._config = config_factory()
        self._timeout = timeout
        self._cache: Cache = Cache(
            CacheConfig(isolation_strategy=IsolationStrategy.TENANT)
        )

    def get_session(self, tenant_subdomain: Optional[str] = None) -> OAuth2Session:
        has_changed = getattr(self._config_factory, "has_changed", None)
        if callable(has_changed) and has_changed():
            logger.debug("Invalidating token cache due to secret rotation")
            self._cache.reset()

        cached: OAuth2Session | None = self._cache.get(
            _TOKEN_NAMESPACE, _token_key(tenant_subdomain)
        )
        if cached is not None:
            return cached

        return self._fetch_token(tenant_subdomain)

    def _fetch_token(self, tenant_subdomain: Optional[str]) -> OAuth2Session:
        self._config = self._config_factory()
        logger.debug(
            "Fetching new OAuth2 token from %s (tenant=%r, base_url=%r)",
            self._config.token_url,
            tenant_subdomain,
            getattr(self._config, "base_url", None),
        )

        token_url = self._config.token_url
        identityzone = self._config.identityzone
        if (
            tenant_subdomain is not None
            and identityzone is not None
            and token_url is not None
        ):
            _validate_tenant_subdomain(tenant_subdomain)
            token_url = _derive_tenant_token_url(
                str(token_url), str(identityzone), tenant_subdomain
            )

        client = BackendApplicationClient(client_id=str(self._config.client_id))
        oauth = OAuth2Session(client=client)
        try:
            token = oauth.fetch_token(
                token_url=token_url,
                client_id=str(self._config.client_id),
                client_secret=str(self._config.client_secret),
                include_client_id=True,
                timeout=self._timeout,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to obtain OAuth2 token: {exc}") from exc

        expires_in: int = token.get("expires_in", 3600)
        ttl = max(expires_in - _TOKEN_EXPIRY_BUFFER_SECONDS, 1)

        key = _token_key(tenant_subdomain)
        # Close the stale session before overwriting to release its connection pool.
        stale: OAuth2Session | None = self._cache.get(_TOKEN_NAMESPACE, key)
        if stale is not None:
            stale.close()
        self._cache.set(_TOKEN_NAMESPACE, key, oauth, ttl_seconds=ttl)

        logger.debug(
            "Obtained OAuth2 token for tenant=%r (expires in %ds)",
            tenant_subdomain,
            expires_in,
        )
        return oauth

    def invalidate(self, tenant_subdomain: Optional[str] = None) -> None:
        self._cache.evict(_TOKEN_NAMESPACE, _token_key(tenant_subdomain))

    def invalidate_all(self) -> None:
        self._cache.reset()

    def close(self) -> None:
        self.invalidate_all()

    @property
    def base_url(self) -> Optional[str]:
        """Current base URL from the most recently read config.

        Updated on every token refresh so callers always get a fresh URL after
        secret rotation.  Returns ``None`` when the underlying config does not
        expose a ``base_url`` attribute (e.g. the destination module uses ``url``).
        """
        return getattr(self._config, "base_url", None)


def _token_key(tenant_subdomain: Optional[str]) -> str:
    return tenant_subdomain if tenant_subdomain is not None else "__provider__"
