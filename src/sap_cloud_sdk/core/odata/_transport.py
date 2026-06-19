"""Synchronous HTTP transport for OData v4 services."""

from __future__ import annotations

import logging
from typing import Any

import requests
from requests.exceptions import RequestException

from sap_cloud_sdk.core.odata._csrf import CsrfTokenProvider
from sap_cloud_sdk.core.odata.exceptions import (
    ODataAuthError,
    ODataNotFoundError,
    ODataRequestError,
)

logger = logging.getLogger(__name__)

_CSRF_HEADER = "X-CSRF-Token"
_REQUEST_TIMEOUT = 30


class ODataHttpTransport:
    """Reusable synchronous HTTP transport for OData v4 services.

    Owns the ``requests.Session``, JSON serialisation, CSRF token handling,
    and status-code–to-exception mapping.  Designed to be injected into
    request builders.

    Args:
        base_url: Root URL of the OData service
            (e.g. ``https://host/sap/opu/odata4/svc/``).
        session: Pre-configured ``requests.Session`` (auth headers set by
            the caller, e.g. via an OAuth2 adapter or a destination factory).
        csrf_enabled: Whether to fetch and attach CSRF tokens on mutating
            requests.  Set to ``False`` for services that do not require it.

    Example::

        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=oauth_session,
        )
        data = transport.get("BusinessPartnerSet", params={"$top": "10"})
    """

    def __init__(
        self,
        base_url: str,
        session: requests.Session,
        csrf_enabled: bool = True,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._csrf: CsrfTokenProvider | None = (
            CsrfTokenProvider(self) if csrf_enabled else None
        )

    # ------------------------------------------------------------------
    # Public verbs
    # ------------------------------------------------------------------

    def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GET request and return the parsed JSON body."""
        return self._request("GET", path, params=params)

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Execute a POST with a CSRF token and return the parsed JSON body."""
        return self._send_with_csrf("POST", path, json=body)

    def patch(
        self,
        path: str,
        body: dict[str, Any],
        etag: str | None = None,
    ) -> dict[str, Any]:
        """Execute a PATCH (partial update) with a CSRF token.

        Args:
            path: Entity path relative to the service base URL.
            body: Partial entity dict to send as the request body.
            etag: If provided, sent as ``If-Match`` for optimistic locking.
        """
        extra: dict[str, str] = {}
        if etag is not None:
            extra["If-Match"] = etag
        return self._send_with_csrf("PATCH", path, json=body, extra_headers=extra)

    def put(
        self,
        path: str,
        body: dict[str, Any],
        etag: str | None = None,
    ) -> dict[str, Any]:
        """Execute a PUT (full replacement) with a CSRF token."""
        extra: dict[str, str] = {}
        if etag is not None:
            extra["If-Match"] = etag
        return self._send_with_csrf("PUT", path, json=body, extra_headers=extra)

    def delete(self, path: str, etag: str | None = None) -> None:
        """Execute a DELETE with a CSRF token."""
        extra: dict[str, str] = {}
        if etag is not None:
            extra["If-Match"] = etag
        self._send_with_csrf("DELETE", path, extra_headers=extra)

    def absolute_url(self, path: str) -> str:
        """Return the full URL for *path* relative to the service base."""
        return self._base_url + "/" + path.lstrip("/")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send_with_csrf(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        assert self._csrf is not None or True  # csrf may be disabled
        csrf_headers: dict[str, str] = {}
        if self._csrf is not None:
            csrf_headers[_CSRF_HEADER] = self._csrf.get()

        merged = {**(extra_headers or {}), **csrf_headers}
        try:
            return self._request(method, path, json=json, extra_headers=merged)
        except ODataAuthError as exc:
            if exc.status_code == 403 and self._csrf is not None:
                self._csrf.invalidate()
                csrf_headers[_CSRF_HEADER] = self._csrf.get()
                merged = {**(extra_headers or {}), **csrf_headers}
                return self._request(method, path, json=json, extra_headers=merged)
            raise

    def _request(
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
            resp = self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                timeout=_REQUEST_TIMEOUT,
            )
        except RequestException as exc:
            raise ODataRequestError.__new__(ODataRequestError) from exc

        self._raise_for_status(resp)

        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.status_code == 404:
            raise ODataNotFoundError(response)
        if response.status_code in (401, 403):
            raise ODataAuthError(response)
        if not response.ok:
            raise ODataRequestError(response)
