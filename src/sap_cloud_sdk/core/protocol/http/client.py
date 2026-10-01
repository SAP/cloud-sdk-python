"""Concrete HTTP client with injectable auth and rotation-resilient retry."""

from __future__ import annotations

from typing import Any, Optional

import requests

from sap_cloud_sdk.core.protocol.http.models import (
    AuthProvider,
    HttpMethod,
    _DEFAULT_TIMEOUT,
)


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
        self._plain_session: Optional[requests.Session] = (
            requests.Session() if auth_provider is None else None
        )

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
