"""HTTP authentication providers and method enum."""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from enum import Enum

import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests.adapters import HTTPAdapter
from requests_oauthlib import OAuth2Session

from sap_cloud_sdk.core._tenant import (
    _validate_tenant_subdomain,
    _derive_tenant_token_url,
)

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
                logger.debug("Invalidating token cache due to secret rotation")
                self._invalidate_all_unsafe()

        with self._lock:
            cached = self._cache.get(tenant_subdomain)
            if cached is not None:
                oauth, expires_at = cached
                if datetime.now() < expires_at:
                    return oauth

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
        with self._lock:
            self._invalidate_all_unsafe()

    def _invalidate_all_unsafe(self) -> None:
        """Invalidate all cached sessions. Caller must hold ``self._lock``."""
        for oauth, _ in self._cache.values():
            oauth.close()
        self._cache.clear()

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


class _BorrowedSession(requests.Session):
    """A requests.Session that does not close its mounted adapters on close().

    Used by IasAuthProvider to share a single HTTPAdapter (and its underlying
    urllib3 connection pool) across per-request sessions without the session's
    close() / __del__ draining the shared pool prematurely.
    """

    def close(self) -> None:
        # Unmount adapters so they are no longer referenced by this session,
        # but do NOT call adapter.close() — the pool is owned by the provider.
        self.adapters.clear()


class IasAuthProvider(AuthProvider):
    """Bearer-token auth provider for IAS (Identity Authentication Service).

    Unlike :class:`XsuaaAuthProvider`, this provider holds no credentials and
    fetches no token. In IAS mode the token is supplied *per request* by the
    caller's runtime: the IAS context provider (wired via ``bootstrap(app)``)
    parses the inbound ``Authorization`` header and stores the raw bearer token
    in the request :class:`~sap_cloud_sdk.core.runtime_context.RuntimeContext`.
    This provider reads that token at :meth:`get_session` time and attaches it.

    Because the token is read fresh on every call, there is nothing to cache or
    invalidate — ``invalidate``/``invalidate_all`` are no-ops.

    When no token is present the session is returned without an ``Authorization``
    header; enforcing presence is the caller's responsibility (the Agent Memory
    client raises a validation error before dispatching the request).

    A single :class:`~requests.adapters.HTTPAdapter` is shared across all calls
    so that the underlying ``urllib3`` connection pool (and its TCP/TLS
    connections) is reused. Each call still gets its own session so the
    per-request ``Authorization`` header is never shared between threads.
    """

    def __init__(self) -> None:
        self._adapter = HTTPAdapter()

    def get_session(self, tenant_subdomain: Optional[str] = None) -> requests.Session:
        # Imported lazily: runtime_context pulls in sap_cloud_sdk.ias, which would
        # create an import cycle if imported at module load time.
        from sap_cloud_sdk.core.runtime_context import get_context
        from sap_cloud_sdk.core.runtime_context.providers._ias import IAS_TOKEN

        session = _BorrowedSession()
        session.mount("https://", self._adapter)
        session.mount("http://", self._adapter)
        ias_token = get_context().get(IAS_TOKEN)
        if ias_token:
            session.headers["Authorization"] = f"Bearer {ias_token}"
        else:
            logger.debug(
                "IasAuthProvider: no IAS token in context, "
                "session has no Authorization header"
            )
        return session

    def invalidate(self, tenant_subdomain: Optional[str] = None) -> None:
        pass

    def invalidate_all(self) -> None:
        pass

    def close(self) -> None:
        self._adapter.close()
