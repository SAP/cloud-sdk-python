"""HTTP authentication providers and method enum."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Optional

import requests
from oauthlib.oauth2 import BackendApplicationClient
from oauthlib.oauth2.rfc6749.errors import FatalClientError
from requests.adapters import HTTPAdapter
from requests_oauthlib import OAuth2Session

from sap_cloud_sdk.core.resilience.cache._cache import Cache
from sap_cloud_sdk.core.resilience.cache._config import CacheConfig
from sap_cloud_sdk.core.resilience.cache._isolation import IsolationStrategy
from sap_cloud_sdk.core._tenant import (
    _derive_tenant_token_url,
    _validate_tenant_subdomain,
)

logger = logging.getLogger(__name__)

_TOKEN_EXPIRY_BUFFER_SECONDS = 60
_DEFAULT_TIMEOUT = 30.0
_TOKEN_NAMESPACE = "xsuaa_token"
_TOKEN_FETCH_MAX_ATTEMPTS = 3
_TOKEN_FETCH_BACKOFF_BASE = 0.5  # seconds; delay = base * 2^attempt


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
    SDK ``Cache`` module. Re-reads credentials from the binding on every token
    refresh so that rotated secrets are picked up automatically. Detects rotation
    proactively by checking the secret directory mtime before each cache hit via
    ``has_changed()``.

    Args:
        config_factory: A ``ConfigFactory`` (or any callable with a
            ``has_changed() -> bool`` method) that returns fresh XSUAA
            credentials on every call.
        timeout: Timeout in seconds for token-endpoint requests.
        module: Optional module name passed to ``Cache``.
            Instances with the same name share one backend, which keeps the token
            cache alive across per-request client re-creation. Callers that create
            a single long-lived provider can omit this.
    """

    def __init__(
        self,
        config_factory: Callable[[], Any],
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        module: str | None = None,
    ) -> None:
        self._config_factory = config_factory
        self._config = config_factory()
        self._timeout = timeout
        self._cache: Cache = Cache(
            CacheConfig(isolation_strategy=IsolationStrategy.TENANT),
            module=module,
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
        last_exc: Exception | None = None
        for attempt in range(_TOKEN_FETCH_MAX_ATTEMPTS):
            try:
                token = oauth.fetch_token(
                    token_url=token_url,
                    client_id=str(self._config.client_id),
                    client_secret=str(self._config.client_secret),
                    include_client_id=True,
                    timeout=self._timeout,
                )
                last_exc = None
                break
            except FatalClientError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < _TOKEN_FETCH_MAX_ATTEMPTS - 1:
                    delay = _TOKEN_FETCH_BACKOFF_BASE * (2**attempt)
                    logger.warning(
                        "OAuth2 token fetch failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        _TOKEN_FETCH_MAX_ATTEMPTS,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
        if last_exc is not None:
            raise RuntimeError(
                f"Failed to obtain OAuth2 token after {_TOKEN_FETCH_MAX_ATTEMPTS} attempts: {last_exc}"
            ) from last_exc

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
