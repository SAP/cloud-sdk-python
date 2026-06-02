"""HTTP client wrappers for SAP ADM OData V4 service calls.

Provides two transport implementations:
- :class:`AdmsHttp` — sync, ``requests``-based.
- :class:`AsyncAdmsHttp` — async, ``httpx``-based (extends core AsyncHttpClient).

Both handle:
- ``Authorization: Bearer`` injection on every request.
- OData ``X-CSRF-Token`` fetch-and-carry for state-changing requests (POST,
  PUT, PATCH, DELETE), cached per OData service root to avoid cross-service
  token reuse.
- Consistent ADMS error propagation.
"""

from __future__ import annotations

from typing import Any

import httpx
import requests
from requests import Response
from requests.exceptions import RequestException

from sap_cloud_sdk.adms._auth import IasTokenFetcher
from sap_cloud_sdk.adms.config import AdmsConfig
from sap_cloud_sdk.adms.exceptions import DocumentNotFoundError, HttpError
from sap_cloud_sdk.core.http import AsyncHttpClient
from sap_cloud_sdk.core.http import HttpError as CoreHttpError
from sap_cloud_sdk.core.http import NotFoundError as CoreNotFoundError

_CSRF_FETCH_HEADER = "X-CSRF-Token"
_CSRF_FETCH_VALUE = "Fetch"


def quote_odata_string_key(value: str) -> str:
    """Quote and escape a string value for use in an OData V4 entity key segment.

    OData V4 §5.1.1.6.2 requires single-quoted string literals with embedded
    single quotes doubled.  Without escaping, a value like ``O'Brien`` (or a
    deliberately crafted ``'); ...``) breaks the URL or alters query intent.

    Example::

        path = f"Documents(DocID={quote_odata_string_key(doc_id)})"
    """
    return "'" + value.replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# Sync HTTP wrapper
# ---------------------------------------------------------------------------


class AdmsHttp:
    """Thin sync HTTP wrapper for ADM OData V4 service.

    Manages:
    * Bearer token injection via :class:`IasTokenFetcher`.
    * CSRF token fetch-and-carry for mutating requests, cached per service root.
    * Consistent error propagation.

    Args:
        config: AdmsConfig with service URL and IAS credentials.
        token_fetcher: IasTokenFetcher instance (injected for testability).
        session: Optional requests.Session to reuse across calls.
        user_jwt: Optional user JWT for OBO token exchange.
    """

    def __init__(
        self,
        config: AdmsConfig,
        token_fetcher: IasTokenFetcher,
        session: requests.Session | None = None,
        user_jwt: str | None = None,
    ) -> None:
        self._config = config
        self._token_fetcher = token_fetcher
        self._session = session or requests.Session()
        self._user_jwt = user_jwt
        self._csrf_tokens: dict[str, str] = {}

    def with_user_jwt(self, user_jwt: str) -> "AdmsHttp":
        """Return a new :class:`AdmsHttp` configured for user-context calls.

        Args:
            user_jwt: The user's OIDC or XSUAA JWT from the inbound request.

        Returns:
            New :class:`AdmsHttp` for user-context calls.
        """
        return AdmsHttp(
            config=self._config,
            token_fetcher=self._token_fetcher,
            session=self._session,
            user_jwt=user_jwt,
        )

    # ------------------------------------------------------------------
    # Public HTTP verbs
    # ------------------------------------------------------------------

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> Response:
        return self._request("GET", path, params=params, service_base=service_base)

    def post(
        self,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> Response:
        return self._send_with_csrf(
            "POST", path, json=json, params=params, service_base=service_base
        )

    def delete(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> Response:
        return self._send_with_csrf(
            "DELETE", path, params=params, service_base=service_base
        )

    def patch(
        self,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> Response:
        return self._send_with_csrf(
            "PATCH", path, json=json, params=params, service_base=service_base
        )

    def _send_with_csrf(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> Response:
        csrf = self._get_csrf_token(service_base)
        try:
            return self._request(
                method,
                path,
                json=json,
                params=params,
                service_base=service_base,
                extra_headers={_CSRF_FETCH_HEADER: csrf},
            )
        except HttpError as exc:
            if exc.status_code != 403:
                raise
            # CSRF tokens have server-side TTLs; on 403, evict the cached token,
            # re-fetch, and retry once before giving up.
            self._csrf_tokens.pop(service_base or "", None)
            csrf = self._get_csrf_token(service_base)
            return self._request(
                method,
                path,
                json=json,
                params=params,
                service_base=service_base,
                extra_headers={_CSRF_FETCH_HEADER: csrf},
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _bearer_token(self) -> str:
        if self._user_jwt:
            return self._token_fetcher.exchange_token(self._user_jwt)
        return self._token_fetcher.get_token()

    def _get_csrf_token(self, service_base: str | None = None) -> str:
        """Return the CSRF token for this service root, fetching if not cached.

        Uses ``self._session.get`` directly (not :meth:`_request`) so the
        response status is *not* error-checked — many OData services return
        403/405 on the bare service root yet still echo back a valid
        ``X-CSRF-Token`` response header, which is all we need.
        """
        key = service_base or ""
        if key in self._csrf_tokens:
            return self._csrf_tokens[key]

        base = self._resolve_base(service_base)
        url = f"{base}/"
        try:
            resp = self._session.get(
                url,
                headers={
                    "Authorization": f"Bearer {self._bearer_token()}",
                    _CSRF_FETCH_HEADER: _CSRF_FETCH_VALUE,
                },
                timeout=10,
            )
        except RequestException as exc:
            raise HttpError(f"CSRF fetch request failed: {exc}") from exc

        csrf = resp.headers.get(_CSRF_FETCH_HEADER, "")
        self._csrf_tokens[key] = csrf
        return csrf

    def _resolve_base(self, service_base: str | None) -> str:
        svc = service_base or ""
        return self._config.service_url.rstrip("/") + "/" + svc.lstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        extra_headers: dict[str, str] | None = None,
        service_base: str | None = None,
    ) -> Response:
        base = self._resolve_base(service_base)
        url = base.rstrip("/") + "/" + path.lstrip("/")
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._bearer_token()}",
        }
        if extra_headers:
            headers.update(extra_headers)

        try:
            resp = self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                timeout=30,
            )
        except RequestException as exc:
            raise HttpError(f"ADMS request failed: {exc}") from exc

        if resp.status_code == 404:
            raise DocumentNotFoundError(f"Resource not found: {method} {url}")

        if not (200 <= resp.status_code < 300):
            raise HttpError(
                f"ADMS service returned HTTP {resp.status_code}",
                status_code=resp.status_code,
                response_text=resp.text,
            )

        return resp


# ---------------------------------------------------------------------------
# Async HTTP wrapper
# ---------------------------------------------------------------------------


class AsyncAdmsHttp(AsyncHttpClient):
    """Async HTTP wrapper for ADM OData V4 service.

    Extends :class:`~sap_cloud_sdk.core.http.AsyncHttpClient` with:

    * OData CSRF token fetch-and-carry for mutating requests (POST, PATCH,
      DELETE), cached per OData service root.
    * Dynamic ``service_base`` path prefix for multi-root OData services.
    * Mapping of core :class:`~sap_cloud_sdk.core.http.HttpError` /
      :class:`~sap_cloud_sdk.core.http.NotFoundError` to ADMS-specific types.

    Use as an async context manager to ensure the underlying ``httpx.AsyncClient``
    is properly closed::

        async with AsyncAdmsHttp(config, token_fetcher) as http:
            resp = await http.get("Documents", service_base="odata/v4/DocumentService")

    Args:
        config: AdmsConfig with service URL and IAS credentials.
        token_fetcher: IasTokenFetcher instance (shared with sync client).
        client: Optional ``httpx.AsyncClient`` to reuse (useful for testing).
        user_jwt: Optional user JWT for OBO token exchange.
    """

    def __init__(
        self,
        config: AdmsConfig,
        token_fetcher: IasTokenFetcher,
        client: httpx.AsyncClient | None = None,
        user_jwt: str | None = None,
    ) -> None:
        self._config = config
        self._token_fetcher = token_fetcher
        self._user_jwt = user_jwt
        # Default to owning the underlying ``httpx.AsyncClient``.  Borrowed
        # instances created via :meth:`with_user_jwt` flip this to ``False``
        # so they share — and do *not* close — the parent's connection pool.
        self._owns_client = True
        _jwt = user_jwt  # capture for closure before super().__init__()
        get_token = (
            (lambda: token_fetcher.exchange_token(_jwt))
            if _jwt
            else token_fetcher.get_token
        )
        super().__init__(
            base_url=config.service_url,
            get_token=get_token,
            client=client,
        )
        self._csrf_tokens: dict[str, str] = {}

    async def aclose(self) -> None:
        """Close the underlying ``httpx.AsyncClient`` if this instance owns it."""
        if self._owns_client:
            await self._client.aclose()

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # Public async HTTP verbs  (add service_base + CSRF on top of core)
    # ------------------------------------------------------------------

    async def get(  # type: ignore[override]
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> httpx.Response:
        return await self._request(
            "GET", self._prefixed(path, service_base), params=params
        )

    async def post(  # type: ignore[override]
        self,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> httpx.Response:
        return await self._send_with_csrf(
            "POST", path, json=json, params=params, service_base=service_base
        )

    async def delete(  # type: ignore[override]
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> httpx.Response:
        return await self._send_with_csrf(
            "DELETE", path, params=params, service_base=service_base
        )

    async def patch(  # type: ignore[override]
        self,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> httpx.Response:
        return await self._send_with_csrf(
            "PATCH", path, json=json, params=params, service_base=service_base
        )

    async def _send_with_csrf(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        service_base: str | None = None,
    ) -> httpx.Response:
        csrf = await self._get_csrf_token(service_base)
        try:
            return await self._request(
                method,
                self._prefixed(path, service_base),
                json=json,
                params=params,
                extra_headers={_CSRF_FETCH_HEADER: csrf},
            )
        except HttpError as exc:
            if exc.status_code != 403:
                raise
            # CSRF tokens have server-side TTLs; on 403, evict the cached token,
            # re-fetch, and retry once before giving up.
            self._csrf_tokens.pop(service_base or "", None)
            csrf = await self._get_csrf_token(service_base)
            return await self._request(
                method,
                self._prefixed(path, service_base),
                json=json,
                params=params,
                extra_headers={_CSRF_FETCH_HEADER: csrf},
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        content: bytes | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Delegate to core ``_request`` and map exceptions to ADMS types."""
        try:
            return await super()._request(
                method,
                path,
                params=params,
                json=json,
                content=content,
                extra_headers=extra_headers,
            )
        except CoreNotFoundError as exc:
            raise DocumentNotFoundError(str(exc)) from exc
        except CoreHttpError as exc:
            raise HttpError(
                str(exc),
                status_code=exc.status_code,
                response_text=exc.response_text,
            ) from exc

    async def _get_csrf_token(self, service_base: str | None = None) -> str:
        """Return the CSRF token for this service root, fetching if not cached.

        Uses the raw ``httpx`` client directly to avoid triggering error-checking
        on what may be a non-2xx response — many OData services return 403/405
        on the root path but still include the ``X-CSRF-Token`` response header.
        """
        key = service_base or ""
        if key in self._csrf_tokens:
            return self._csrf_tokens[key]

        if service_base:
            url = self._base_url.rstrip("/") + "/" + service_base.strip("/") + "/"
        else:
            url = self._base_url.rstrip("/") + "/"

        bearer = await self._bearer_token()
        try:
            resp = await self._client.get(
                url,
                headers={
                    "Authorization": f"Bearer {bearer}",
                    _CSRF_FETCH_HEADER: _CSRF_FETCH_VALUE,
                },
            )
        except httpx.RequestError as exc:
            raise HttpError(f"Async CSRF fetch request failed: {exc}") from exc

        self._csrf_tokens[key] = resp.headers.get(_CSRF_FETCH_HEADER, "")
        return self._csrf_tokens[key]

    def _prefixed(self, path: str, service_base: str | None) -> str:
        """Prepend *service_base* to *path*, normalising slashes."""
        if service_base:
            return service_base.strip("/") + "/" + path.lstrip("/")
        return path

    def with_user_jwt(self, user_jwt: str) -> "AsyncAdmsHttp":
        """Return a new :class:`AsyncAdmsHttp` configured for user-context calls.

        The new instance **shares** the parent's underlying ``httpx.AsyncClient``
        (and therefore its connection pool) and is marked as non-owning so
        closing it is a no-op.  This avoids leaking a fresh connection pool
        per user-scoped call (e.g. ``client.with_user_jwt(jwt)`` in a
        request handler) while still letting the original parent close once.

        Args:
            user_jwt: The user's OIDC or XSUAA JWT from the inbound request.

        Returns:
            New :class:`AsyncAdmsHttp` for user-context calls.
        """
        borrowed = AsyncAdmsHttp(
            config=self._config,
            token_fetcher=self._token_fetcher,
            client=self._client,
            user_jwt=user_jwt,
        )
        borrowed._owns_client = False
        return borrowed
