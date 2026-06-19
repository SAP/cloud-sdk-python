"""Asynchronous HTTP transport for OData v4 services."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from sap_cloud_sdk.core.odata._constants import (
    CSRF_FETCH_TIMEOUT,
    CSRF_FETCH_VALUE,
    CSRF_HEADER,
    DEFAULT_HEADERS,
    MUTATING_METHODS,
    REQUEST_TIMEOUT,
)
from sap_cloud_sdk.core.odata.exceptions import (
    ODataAuthError,
    ODataConnectionError,
    ODataCsrfError,
    ODataNotFoundError,
    ODataRequestError,
)

logger = logging.getLogger(__name__)


class AsyncODataHttpTransport:
    """Asynchronous HTTP transport for OData v4 services.

    Mirrors :class:`~sap_cloud_sdk.core.odata._transport.ODataHttpTransport`
    but uses ``httpx.AsyncClient``.  Use as an async context manager::

        async with AsyncODataHttpTransport(base_url, client) as t:
            data = await t.request("GET", "BusinessPartnerSet")

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

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute an OData request and return the parsed JSON body.

        CSRF tokens are fetched and attached automatically for mutating methods
        (POST, PUT, PATCH, DELETE) when ``csrf_enabled`` is ``True``.  On a
        403 response the cached token is invalidated and the request is retried
        once with a fresh token.

        Args:
            method: HTTP method (``"GET"``, ``"POST"``, ``"PATCH"``, etc.).
            path: Entity path relative to the service base URL.
            params: OData query parameters.
            json: Request body serialised as JSON.
            headers: Extra headers merged on top of the defaults.

        Returns:
            Parsed JSON response body, or ``{}`` for 204 / empty responses.
        """
        extra = dict(headers or {})

        if method.upper() in MUTATING_METHODS and self._csrf_enabled:
            extra[CSRF_HEADER] = await self._get_csrf_token()
            try:
                return await self._execute(
                    method, path, params=params, json=json, extra_headers=extra
                )
            except ODataAuthError as exc:
                if exc.status_code == 403:
                    await self._invalidate_csrf_token()
                    extra[CSRF_HEADER] = await self._get_csrf_token()
                    return await self._execute(
                        method, path, params=params, json=json, extra_headers=extra
                    )
                raise

        return await self._execute(
            method, path, params=params, json=json, extra_headers=extra
        )

    def absolute_url(self, path: str) -> str:
        return self._base_url + "/" + path.lstrip("/")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

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
                headers={CSRF_HEADER: CSRF_FETCH_VALUE},
                timeout=CSRF_FETCH_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise ODataCsrfError(f"Async CSRF fetch failed: {exc}") from exc

        token = resp.headers.get(CSRF_HEADER, "")
        if not token:
            raise ODataCsrfError(
                f"Service did not return a CSRF token (HTTP {resp.status_code})"
            )
        return token

    async def _execute(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self.absolute_url(path)
        req_headers = {**DEFAULT_HEADERS, **(extra_headers or {})}

        logger.debug("%s %s params=%s", method, url, params)
        try:
            resp = await self._client.request(
                method=method,
                url=url,
                headers=req_headers,
                params=params,
                json=json,
                timeout=REQUEST_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise ODataConnectionError(f"Request failed: {exc}") from exc

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
