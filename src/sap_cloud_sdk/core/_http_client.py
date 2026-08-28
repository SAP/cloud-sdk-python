"""Shared HTTP client with injectable authentication and rotation-resilient token management.

Provides three building blocks used by all service modules:

- :class:`AuthProvider` — abstract interface for authentication strategies.
- :class:`XsuaaAuthProvider` — OAuth2 client-credentials for XSUAA. Re-reads
  credentials on every token refresh and detects secret rotation proactively
  via filesystem mtime.
- :class:`HttpClient` — concrete HTTP client. Composes with an
  :class:`AuthProvider` and retries once on 401 to recover from rotated tokens.
"""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import requests
from enum import Enum
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

logger = logging.getLogger(__name__)

_TOKEN_EXPIRY_BUFFER_SECONDS = 60
_DEFAULT_TIMEOUT = 30.0


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

    Caches tokens per tenant subdomain with expiry-aware eviction.
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
        self._cache: dict[Optional[str], tuple[OAuth2Session, datetime]] = {}
        self._lock = threading.Lock()

    def get_session(self, tenant_subdomain: Optional[str] = None) -> OAuth2Session:
        has_changed = getattr(self._config_factory, "has_changed", None)
        if callable(has_changed) and has_changed():
            with self._lock:
                self.invalidate_all()

        with self._lock:
            cached = self._cache.get(tenant_subdomain)
            if cached is not None:
                oauth, expires_at = cached
                if datetime.now() < expires_at:
                    return oauth

        return self._fetch_token(tenant_subdomain)

    def _fetch_token(self, tenant_subdomain: Optional[str]) -> OAuth2Session:
        self._config = self._config_factory()

        token_url = self._config.token_url
        identityzone = self._config.identityzone
        if (
            tenant_subdomain is not None
            and identityzone is not None
            and token_url is not None
        ):
            token_url = str(token_url).replace(str(identityzone), tenant_subdomain)

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
        expires_at = datetime.now() + timedelta(
            seconds=expires_in - _TOKEN_EXPIRY_BUFFER_SECONDS
        )

        with self._lock:
            existing = self._cache.get(tenant_subdomain)
            if existing is not None:
                existing[0].close()
            self._cache[tenant_subdomain] = (oauth, expires_at)

        logger.debug(
            "Obtained OAuth2 token for tenant=%r (expires in %ds)",
            tenant_subdomain,
            expires_in,
        )
        return oauth

    def invalidate(self, tenant_subdomain: Optional[str] = None) -> None:
        with self._lock:
            self._cache.pop(tenant_subdomain, None)

    def invalidate_all(self) -> None:
        for oauth, _ in self._cache.values():
            oauth.close()
        self._cache.clear()

    def close(self) -> None:
        with self._lock:
            self.invalidate_all()


class HttpClient:
    """Concrete HTTP client with injectable auth and single-retry on 401.

    Returns raw :class:`requests.Response` objects — callers are responsible
    for error handling and domain-specific exception mapping.

    On a 401 response the client evicts the stale token via
    :meth:`AuthProvider.invalidate` and retries the request exactly once. This
    recovers from credentials that were revoked after secret rotation.

    Args:
        base_url: Base URL for all requests (trailing slash is stripped).
        auth_provider: Authentication provider. Pass ``None`` for unauthenticated
            (plain :class:`requests.Session`) mode.
        timeout: Timeout in seconds for resource-server requests.
    """

    def __init__(
        self,
        base_url: str,
        auth_provider: Optional[AuthProvider] = None,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth_provider = auth_provider
        self._timeout = timeout
        self._plain_session: Optional[requests.Session] = None

    def request(
        self,
        method: HttpMethod | str,
        path: str,
        *,
        tenant_subdomain: Optional[str] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Execute a request, retrying once on 401.

        Args:
            method: HTTP verb (``"GET"``, ``"POST"``, etc.).
            path: Path appended to ``base_url``. Should start with ``/``.
            tenant_subdomain: Subscriber tenant subdomain forwarded to the auth
                provider for per-tenant token derivation.
            **kwargs: Forwarded verbatim to :meth:`requests.Session.request`.

        Returns:
            Raw :class:`requests.Response`. Callers must check the status code.
        """
        response = self._execute(method, path, tenant_subdomain, **kwargs)
        if response.status_code == 401 and self._auth_provider is not None:
            self._auth_provider.invalidate(tenant_subdomain)
            response = self._execute(method, path, tenant_subdomain, **kwargs)
        return response

    def _execute(
        self,
        method: HttpMethod | str,
        path: str,
        tenant_subdomain: Optional[str],
        **kwargs: Any,
    ) -> requests.Response:
        method_str = (
            method.value if isinstance(method, HttpMethod) else str(method).upper()
        )
        if self._auth_provider is not None:
            session: requests.Session = self._auth_provider.get_session(
                tenant_subdomain
            )
        else:
            if self._plain_session is None:
                self._plain_session = requests.Session()
            session = self._plain_session
        return session.request(
            method_str,
            f"{self._base_url}{path}",
            timeout=self._timeout,
            **kwargs,
        )

    def close(self) -> None:
        """Close all underlying sessions and release resources."""
        if self._auth_provider is not None:
            self._auth_provider.close()
        if self._plain_session is not None:
            self._plain_session.close()
            self._plain_session = None
