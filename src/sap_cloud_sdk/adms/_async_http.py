"""Generic async HTTP client for SAP Cloud SDK modules.

Provides :class:`AsyncHttpClient` — a thin ``httpx``-based async HTTP wrapper
that handles:

* Bearer token injection via a pluggable ``get_token`` callable.
* Consistent error propagation (:class:`HttpError`, :class:`NotFoundError`).
* Async context manager protocol for proper connection cleanup.

This client is intentionally **service-agnostic** — it knows nothing about
OData, CSRF tokens, or any specific SAP service.  Use it as the foundation
for any SDK module that needs async HTTP with IAS Bearer auth.

Usage::

    from sap_cloud_sdk.adms import AsyncHttpClient
    from sap_cloud_sdk.adms import IasTokenFetcher

    fetcher = IasTokenFetcher(ias_url=..., client_id=..., client_secret=...)

    async with AsyncHttpClient(
        base_url="https://my-service.cfapps.eu20.hana.ondemand.com",
        get_token=fetcher.get_token,
    ) as client:
        resp = await client.get("/api/v1/items")
        data = resp.json()
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Optional

import httpx

# Cap on ``response_text`` carried on error exceptions.  Some upstreams (e.g.
# misconfigured ingresses) return very large HTML error bodies on failures —
# attaching the full body to every exception leads to noisy logs and, if the
# body embeds internal hostnames or stack traces, information disclosure.
_RESPONSE_TEXT_TRUNCATION_LIMIT = 500


class HttpError(Exception):
    """Raised for non-2xx HTTP responses.

    Attributes:
        status_code: HTTP status code.
        message: Human-readable message.
        response_text: Raw response body for diagnostics.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class NotFoundError(HttpError):
    """Raised when the server returns HTTP 404."""


class AsyncHttpClient:
    """Generic async HTTP client with optional Bearer token injection.

    Args:
        base_url: Service root URL (e.g. ``https://api.example.com``).
            All relative paths passed to the HTTP verbs are appended to this.
        get_token: Optional callable (sync or async) that returns a Bearer
            token string.  When async, it is awaited; when sync, it is run
            in the default thread pool via :func:`asyncio.to_thread`.
        client: Optional ``httpx.AsyncClient`` to reuse (useful for testing).
        default_headers: Static headers added to every request (merged with
            per-request headers; per-request headers take precedence).
        timeout: Request timeout in seconds (default 30).

    Example — service-to-service with IAS::

        from sap_cloud_sdk.adms import IasTokenFetcher
        from sap_cloud_sdk.adms import AsyncHttpClient

        fetcher = IasTokenFetcher(ias_url=..., client_id=..., client_secret=...)
        async with AsyncHttpClient(base_url=..., get_token=fetcher.get_token) as http:
            data = (await http.get("/items")).json()
    """

    def __init__(
        self,
        base_url: str,
        get_token: Optional[Callable[[], Any]] = None,
        client: Optional[httpx.AsyncClient] = None,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._get_token = get_token
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._default_headers: Dict[str, str] = default_headers or {}

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AsyncHttpClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Public HTTP verbs
    # ------------------------------------------------------------------

    async def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Perform an async GET request.

        Args:
            path: URL path relative to *base_url* (leading ``/`` is normalised).
            params: URL query parameters.
            headers: Extra headers merged onto the request.

        Returns:
            :class:`httpx.Response` for a 2xx response.

        Raises:
            NotFoundError: On HTTP 404.
            HttpError: On any other non-2xx response.
        """
        return await self._request("GET", path, params=params, extra_headers=headers)

    async def post(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        content: Optional[bytes] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Perform an async POST request."""
        return await self._request(
            "POST",
            path,
            json=json,
            content=content,
            params=params,
            extra_headers=headers,
        )

    async def patch(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Perform an async PATCH request."""
        return await self._request(
            "PATCH",
            path,
            json=json,
            params=params,
            extra_headers=headers,
        )

    async def put(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        content: Optional[bytes] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Perform an async PUT request."""
        return await self._request(
            "PUT",
            path,
            json=json,
            content=content,
            params=params,
            extra_headers=headers,
        )

    async def delete(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Perform an async DELETE request."""
        return await self._request(
            "DELETE",
            path,
            params=params,
            extra_headers=headers,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _bearer_token(self) -> Optional[str]:
        """Resolve the bearer token, handling both sync and async callables."""
        if self._get_token is None:
            return None
        if asyncio.iscoroutinefunction(self._get_token):
            return await self._get_token()
        return await asyncio.to_thread(self._get_token)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        content: Optional[bytes] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        url = self._base_url + "/" + path.lstrip("/")
        token = await self._bearer_token()

        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        headers.update(self._default_headers)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers:
            headers.update(extra_headers)

        try:
            resp = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                content=content,
            )
        except httpx.RequestError as exc:
            raise HttpError(f"Request failed [{method} {url}]: {exc}") from exc

        if resp.status_code == 404:
            raise NotFoundError(
                f"Resource not found: {method} {url}",
                status_code=404,
                response_text=resp.text[:_RESPONSE_TEXT_TRUNCATION_LIMIT],
            )
        if not resp.is_success:
            raise HttpError(
                f"HTTP {resp.status_code}: {resp.text[:_RESPONSE_TEXT_TRUNCATION_LIMIT]}",
                status_code=resp.status_code,
                response_text=resp.text[:_RESPONSE_TEXT_TRUNCATION_LIMIT],
            )
        return resp
