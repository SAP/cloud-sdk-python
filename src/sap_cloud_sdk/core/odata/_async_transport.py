"""Asynchronous HTTP transport for OData v4 services."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from sap_cloud_sdk.core.odata.exceptions import (
    ODataAuthError,
    ODataCsrfError,
    ODataNotFoundError,
    ODataRequestError,
)

logger = logging.getLogger(__name__)

_CSRF_HEADER = "X-CSRF-Token"
_CSRF_FETCH_VALUE = "Fetch"
_CSRF_FETCH_TIMEOUT = 10
_REQUEST_TIMEOUT = 30


class AsyncODataHttpTransport:
    """Asynchronous HTTP transport for OData v4 services.

    Mirrors :class:`~sap_cloud_sdk.core.odata._transport.ODataHttpTransport`
    but uses ``httpx.AsyncClient``.  Use as an async context manager::

        async with AsyncODataHttpTransport(base_url, client) as t:
            data = await t.get("BusinessPartnerSet")

    Args:
        base_url: Root URL of the OData service.
        client: Pre-configured ``httpx.AsyncClient``.
        csrf_enabled: Whether to fetch and attach CSRF tokens on mutating
            requests.
    """

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient,
        csrf_enabled: bool = True,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._csrf_enabled = csrf_enabled
        self._csrf_token: str | None = None
        self._csrf_lock = asyncio.Lock()

    async def __aenter__(self) -> "AsyncODataHttpTransport":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Public verbs
    # ------------------------------------------------------------------

    async def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GET and return the parsed JSON body."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Execute a POST with CSRF and return the parsed JSON body."""
        return await self._send_with_csrf("POST", path, json=body)

    async def patch(
        self,
        path: str,
        body: dict[str, Any],
        etag: str | None = None,
    ) -> dict[str, Any]:
        extra: dict[str, str] = {}
        if etag is not None:
            extra["If-Match"] = etag
        return await self._send_with_csrf("PATCH", path, json=body, extra_headers=extra)

    async def put(
        self,
        path: str,
        body: dict[str, Any],
        etag: str | None = None,
    ) -> dict[str, Any]:
        extra: dict[str, str] = {}
        if etag is not None:
            extra["If-Match"] = etag
        return await self._send_with_csrf("PUT", path, json=body, extra_headers=extra)

    async def delete(self, path: str, etag: str | None = None) -> None:
        extra: dict[str, str] = {}
        if etag is not None:
            extra["If-Match"] = etag
        await self._send_with_csrf("DELETE", path, extra_headers=extra)

    def absolute_url(self, path: str) -> str:
        return self._base_url + "/" + path.lstrip("/")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _send_with_csrf(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        csrf_headers: dict[str, str] = {}
        if self._csrf_enabled:
            csrf_headers[_CSRF_HEADER] = await self._get_csrf_token()

        merged = {**(extra_headers or {}), **csrf_headers}
        try:
            return await self._request(method, path, json=json, extra_headers=merged)
        except ODataAuthError as exc:
            if exc.status_code == 403 and self._csrf_enabled:
                await self._invalidate_csrf_token()
                csrf_headers[_CSRF_HEADER] = await self._get_csrf_token()
                merged = {**(extra_headers or {}), **csrf_headers}
                return await self._request(method, path, json=json, extra_headers=merged)
            raise

    async def _get_csrf_token(self) -> str:
        async with self._csrf_lock:
            if self._csrf_token is not None:
                return self._csrf_token

        token = await self._fetch_csrf_token()
        async with self._csrf_lock:
            if self._csrf_token is None:
                self._csrf_token = token
            return self._csrf_token  # type: ignore[return-value]

    async def _invalidate_csrf_token(self) -> None:
        async with self._csrf_lock:
            self._csrf_token = None

    async def _fetch_csrf_token(self) -> str:
        url = self._base_url + "/"
        try:
            resp = await self._client.get(
                url,
                headers={_CSRF_HEADER: _CSRF_FETCH_VALUE},
                timeout=_CSRF_FETCH_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise ODataCsrfError(f"Async CSRF fetch failed: {exc}") from exc

        token = resp.headers.get(_CSRF_HEADER, "")
        if not token:
            raise ODataCsrfError(
                f"Service did not return a CSRF token (HTTP {resp.status_code})"
            )
        return token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self.absolute_url(path)
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        logger.debug("%s %s params=%s", method, url, params)
        try:
            resp = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                timeout=_REQUEST_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise ODataCsrfError(f"Request failed: {exc}") from exc

        self._raise_for_status(resp)

        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 404:
            raise ODataNotFoundError(_HttpxResponseAdapter(response))
        if response.status_code in (401, 403):
            raise ODataAuthError(_HttpxResponseAdapter(response))
        if not (200 <= response.status_code < 300):
            raise ODataRequestError(_HttpxResponseAdapter(response))


class _HttpxResponseAdapter:
    """Minimal adapter so httpx.Response can be passed to ODataRequestError."""

    def __init__(self, response: httpx.Response) -> None:
        self.status_code = response.status_code
        self._response = response

    def json(self) -> Any:
        return self._response.json()
