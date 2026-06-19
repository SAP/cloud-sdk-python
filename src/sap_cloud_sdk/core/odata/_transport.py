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
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
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
        data = transport.request("GET", "BusinessPartnerSet", params={"$top": "10"})
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

    def request(
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
            params: OData query parameters (``$filter``, ``$top``, …).
            json: Request body serialised as JSON.
            headers: Extra headers merged on top of the defaults
                (``Accept: application/json``, ``Content-Type: application/json``).

        Returns:
            Parsed JSON response body, or ``{}`` for 204 / empty responses.
        """
        extra = dict(headers or {})

        if method.upper() in _MUTATING_METHODS and self._csrf is not None:
            extra[_CSRF_HEADER] = self._csrf.get()
            try:
                return self._execute(method, path, params=params, json=json, extra_headers=extra)
            except ODataAuthError as exc:
                if exc.status_code == 403:
                    self._csrf.invalidate()
                    extra[_CSRF_HEADER] = self._csrf.get()
                    return self._execute(method, path, params=params, json=json, extra_headers=extra)
                raise

        return self._execute(method, path, params=params, json=json, extra_headers=extra)

    def absolute_url(self, path: str) -> str:
        """Return the full URL for *path* relative to the service base."""
        return self._base_url + "/" + path.lstrip("/")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _execute(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self.absolute_url(path)
        req_headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if extra_headers:
            req_headers.update(extra_headers)

        logger.debug("%s %s params=%s", method, url, params)
        try:
            resp = self._session.request(
                method=method,
                url=url,
                headers=req_headers,
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
