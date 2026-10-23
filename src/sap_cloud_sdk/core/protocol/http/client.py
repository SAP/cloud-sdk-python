"""Concrete HTTP client with injectable auth and rotation-resilient retry."""

from __future__ import annotations

from typing import Any, Optional

import requests

from sap_cloud_sdk.cache._cache import Cache
from sap_cloud_sdk.cache._config import CacheConfig
from sap_cloud_sdk.cache._isolation import IsolationStrategy
from sap_cloud_sdk.core.protocol.http.models import (
    AuthProvider,
    HttpMethod,
    _DEFAULT_TIMEOUT,
)

# CSRF handshake constants.  OData/CAP services issue a token on a safe probe
# request carrying ``X-CSRF-Token: Fetch`` and require it echoed back on every
# state-changing request.
_CSRF_HEADER = "X-CSRF-Token"
_CSRF_FETCH_VALUE = "Fetch"
_CSRF_NAMESPACE = "csrf"
_CSRF_DEFAULT_TTL_SECONDS = 1800

# Methods that mutate server state and therefore require a CSRF token.
_CSRF_PROTECTED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class HttpClient:
    """Concrete HTTP client with injectable auth and single-retry on 401.

    Returns raw :class:`requests.Response` objects — callers are responsible
    for error handling and domain-specific exception mapping.

    On a 401 response the client evicts the stale token via
    :meth:`AuthProvider.invalidate` and retries the request exactly once. This
    recovers from credentials that were revoked after secret rotation.

    When *csrf_enabled* is ``True``, state-changing requests (POST, PUT, PATCH,
    DELETE) carry an ``X-CSRF-Token`` fetched from the service root and cached
    via :class:`~sap_cloud_sdk.cache._cache.Cache`. CSRF tokens are
    service-wide (not tenant-scoped), so the cache uses
    :attr:`~sap_cloud_sdk.cache.IsolationStrategy.PROVIDER`. On a 403 response
    the cached token is evicted, re-fetched, and the request retried once.

    Args:
        base_url: Base URL for all requests (trailing slash is stripped).
        auth_provider: Authentication provider. Pass ``None`` for unauthenticated
            (plain :class:`requests.Session`) mode.
        timeout: Timeout in seconds for resource-server requests.
        csrf_enabled: Enable OData/CAP CSRF token fetch-and-carry for mutating
            requests. Defaults to ``False`` so existing callers are unaffected.
    """

    def __init__(
        self,
        base_url: str,
        auth_provider: Optional[AuthProvider] = None,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        csrf_enabled: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth_provider = auth_provider
        self._timeout = timeout
        self._plain_session: Optional[requests.Session] = (
            requests.Session() if auth_provider is None else None
        )
        self._csrf_enabled = csrf_enabled
        self._csrf_cache: Optional[Cache] = (
            Cache(
                CacheConfig(
                    isolation_strategy=IsolationStrategy.PROVIDER,
                    default_ttl_seconds=_CSRF_DEFAULT_TTL_SECONDS,
                )
            )
            if csrf_enabled
            else None
        )

    def request(
        self,
        method: HttpMethod | str,
        path: str,
        *,
        tenant_subdomain: Optional[str] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Execute a request, retrying once on 401 (and once on 403 for CSRF).

        Args:
            method: HTTP verb (``"GET"``, ``"POST"``, etc.).
            path: Path appended to ``base_url``. Should start with ``/``.
            tenant_subdomain: Subscriber tenant subdomain forwarded to the auth
                provider for per-tenant token derivation.
            **kwargs: Forwarded verbatim to :meth:`requests.Session.request`.

        Returns:
            Raw :class:`requests.Response`. Callers must check the status code.
        """
        method_str = (
            method.value if isinstance(method, HttpMethod) else str(method).upper()
        )

        needs_csrf = (
            self._csrf_cache is not None and method_str in _CSRF_PROTECTED_METHODS
        )
        if needs_csrf:
            return self._request_with_csrf(method_str, path, tenant_subdomain, **kwargs)

        response = self._execute(method_str, path, tenant_subdomain, **kwargs)
        if response.status_code == 401 and self._auth_provider is not None:
            self._auth_provider.invalidate(tenant_subdomain)
            response = self._execute(method_str, path, tenant_subdomain, **kwargs)
        return response

    def _request_with_csrf(
        self,
        method_str: str,
        path: str,
        tenant_subdomain: Optional[str],
        **kwargs: Any,
    ) -> requests.Response:
        """Execute a mutating request carrying a CSRF token, retrying on 403.

        On a 403 the cached token is evicted, re-fetched, and the request is
        retried exactly once — CSRF tokens have server-side TTLs and may have
        expired since they were cached.
        """
        token = self._get_csrf_token(tenant_subdomain)
        response = self._execute_with_header(
            method_str, path, tenant_subdomain, token, **kwargs
        )
        if response.status_code == 403:
            assert self._csrf_cache is not None
            self._csrf_cache.evict(_CSRF_NAMESPACE, self._csrf_key())
            token = self._get_csrf_token(tenant_subdomain)
            response = self._execute_with_header(
                method_str, path, tenant_subdomain, token, **kwargs
            )
        return response

    def _execute_with_header(
        self,
        method_str: str,
        path: str,
        tenant_subdomain: Optional[str],
        csrf_token: Optional[str],
        **kwargs: Any,
    ) -> requests.Response:
        headers = {**kwargs.pop("headers", {})}
        if csrf_token:
            headers[_CSRF_HEADER] = csrf_token
        return self._execute(
            method_str, path, tenant_subdomain, headers=headers, **kwargs
        )

    def _get_csrf_token(self, tenant_subdomain: Optional[str]) -> Optional[str]:
        """Return the cached CSRF token for the service root, fetching on miss."""
        assert self._csrf_cache is not None
        key = self._csrf_key()
        cached = self._csrf_cache.get(_CSRF_NAMESPACE, key)
        if cached is not None:
            return cached

        token = self._fetch_csrf_token(tenant_subdomain)
        if token:
            self._csrf_cache.set(_CSRF_NAMESPACE, key, token, ttl_seconds=None)
        return token

    def _fetch_csrf_token(self, tenant_subdomain: Optional[str]) -> Optional[str]:
        """Probe the service root to obtain a fresh CSRF token.

        Uses a GET to the base URL carrying ``X-CSRF-Token: Fetch``. The
        response status is not error-checked — many OData services return a
        non-2xx on the bare root yet still echo back a valid token header.
        """
        if self._auth_provider is not None:
            session = self._auth_provider.get_session(tenant_subdomain)
            base_url = getattr(self._auth_provider, "base_url", None) or self._base_url
        else:
            assert self._plain_session is not None
            session = self._plain_session
            base_url = self._base_url

        resp = session.request(
            "GET",
            f"{base_url}/",
            headers={_CSRF_HEADER: _CSRF_FETCH_VALUE},
            timeout=self._timeout,
        )
        return resp.headers.get(_CSRF_HEADER)

    def _csrf_key(self) -> str:
        """Cache key for the CSRF token — the current effective service root."""
        if self._auth_provider is not None:
            return getattr(self._auth_provider, "base_url", None) or self._base_url
        return self._base_url

    def _execute(
        self,
        method_str: str,
        path: str,
        tenant_subdomain: Optional[str],
        **kwargs: Any,
    ) -> requests.Response:
        if self._auth_provider is not None:
            session: requests.Session = self._auth_provider.get_session(
                tenant_subdomain
            )
            # Use the auth provider's current base_url (updated on every token
            # refresh) so requests go to the correct URL after secret rotation.
            base_url = getattr(self._auth_provider, "base_url", None) or self._base_url
        else:
            assert self._plain_session is not None
            session = self._plain_session
            base_url = self._base_url
        return session.request(
            method_str,
            f"{base_url}{path}",
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
