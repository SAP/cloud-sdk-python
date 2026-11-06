"""HTTP client for calling the target system described by a Destination."""

from __future__ import annotations

import ssl
from enum import Enum
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from requests import Response
from requests.adapters import HTTPAdapter

from sap_cloud_sdk.destination._cert_loader import build_client_cert_context
from sap_cloud_sdk.destination._models import Destination, DestinationType

_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECT_HOPS = 5


class RedirectMode(Enum):
    """Controls whether ``DestinationHttpClient`` follows HTTP redirects.

    Attributes:
        NONE: Never follow redirects (default). The 3xx response is returned
            as-is. Destination credentials are never forwarded beyond the
            configured origin.
        SAME_ORIGIN: Follow redirects only when the ``Location`` URL resolves to
            the same scheme, host, and port as the destination URL. Cross-origin
            redirects, port changes, and HTTPS-to-HTTP downgrades are rejected
            (the redirect response is returned). Hop count is bounded at 5.
    """

    NONE = "none"
    SAME_ORIGIN = "same_origin"


def _parse_origin(url: str) -> tuple[str, str, int]:
    """Return the normalized (scheme, host, effective_port) triple for *url*."""
    p = urlparse(url)
    scheme = p.scheme.lower()
    host = (p.hostname or "").lower()
    port = p.port if p.port is not None else (443 if scheme == "https" else 80)
    return (scheme, host, port)


class _ClientCertAdapter(HTTPAdapter):
    """requests HTTPAdapter that injects a stdlib SSLContext for mTLS."""

    def __init__(self, ssl_ctx: ssl.SSLContext, **kwargs: Any) -> None:
        self._ssl_ctx = ssl_ctx
        super().__init__(**kwargs)

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        kwargs["ssl_context"] = self._ssl_ctx
        super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args: Any, **kwargs: Any) -> Any:
        kwargs["ssl_context"] = self._ssl_ctx
        return super().proxy_manager_for(*args, **kwargs)


class DestinationHttpClient:
    """Wraps requests.Session to call the target system described by a Destination.

    Pre-bakes headers derived from the destination — ERP headers (sap-client,
    sap-language), URL.headers.* properties, and auth tokens. Certificates from the
    destination's certificate list are mounted into the session.

    Redirects are **not** followed by default (``RedirectMode.NONE``). This
    prevents destination credentials pre-baked in the session from being
    forwarded to a different origin. Use ``redirect_mode=RedirectMode.SAME_ORIGIN``
    to allow same-origin relative redirects.

    Use as a context manager to ensure the underlying session is closed:

        with DestinationHttpClient(dest) as http:
            response = http.request("GET", "/api/resource")
    """

    def __init__(
        self,
        destination: Destination,
        *,
        redirect_mode: RedirectMode = RedirectMode.NONE,
    ) -> None:
        if destination.type != DestinationType.HTTP:
            raise ValueError(
                f"DestinationHttpClient only supports HTTP destinations, got: {destination.type}"
            )

        self._session = requests.Session()
        self._session.headers.update(destination.get_headers())
        self._base_url = destination.url.rstrip("/") if destination.url else ""
        self._redirect_mode = redirect_mode
        self._origin = _parse_origin(self._base_url)

        ssl_ctx = build_client_cert_context(destination)
        if ssl_ctx is not None:
            self._session.mount("https://", _ClientCertAdapter(ssl_ctx))

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        """Send an HTTP request to the target system.

        Redirects are not followed by default. Construct with
        ``redirect_mode=RedirectMode.SAME_ORIGIN`` to follow same-origin
        relative redirects. Passing ``allow_redirects`` in ``**kwargs`` has no
        effect — it is silently removed to prevent accidental credential leakage.

        Args:
            method: HTTP verb (GET, POST, PUT, PATCH, DELETE).
            path: Path relative to the destination URL.
            params: Optional query parameters.
            json: Optional JSON body.
            headers: Optional additional headers merged on top of pre-baked ones.
            **kwargs: Passed through to requests.Session.request (except
                ``allow_redirects``, which is always controlled by the
                ``redirect_mode`` set at construction time).

        Returns:
            requests.Response from the target system.
        """
        url = f"{self._base_url}/{path.lstrip('/')}" if path else self._base_url
        kwargs.pop("allow_redirects", None)
        if self._redirect_mode is RedirectMode.SAME_ORIGIN:
            return self._request_following_same_origin(
                method.upper(), url, params=params, json=json, headers=headers, **kwargs
            )
        return self._session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json,
            headers=headers,
            allow_redirects=False,
            **kwargs,
        )

    def _request_following_same_origin(
        self,
        method: str,
        start_url: str,
        *,
        params: Optional[Dict[str, Any]],
        json: Optional[Any],
        headers: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> Response:
        """Follow redirects only when the Location resolves to the same origin.

        Uses a manual hop loop so that ALL credential headers baked into the
        session are protected — not only Authorization (which requests strips
        natively). Every hop is validated before the next request is issued.
        """
        current_url = start_url
        for _ in range(_MAX_REDIRECT_HOPS):
            resp = self._session.request(
                method=method,
                url=current_url,
                params=params,
                json=json,
                headers=headers,
                allow_redirects=False,
                **kwargs,
            )
            if resp.status_code not in _REDIRECT_STATUS_CODES:
                return resp
            location = resp.headers.get("Location")
            if not location:
                return resp
            next_url = urljoin(current_url, location)
            np = urlparse(next_url)
            # Reject userinfo (e.g. http://user:pass@host/) or malformed authority
            if "@" in np.netloc or not np.hostname:
                return resp
            # Reject HTTPS → HTTP downgrade (defense-in-depth on top of origin check)
            if urlparse(current_url).scheme == "https" and np.scheme == "http":
                return resp
            # Reject any change in scheme, host, or effective port
            if _parse_origin(next_url) != self._origin:
                return resp
            # 303 See Other — always convert to GET and drop the request body
            if resp.status_code == 303:
                method, json = "GET", None
            params = None  # Location already encodes the resolved query string
            current_url = next_url
        return resp  # max hops exhausted — return the last redirect response

    def __enter__(self) -> "DestinationHttpClient":
        return self

    def __exit__(self, *exc: Any) -> bool:
        self._session.close()
        return False
