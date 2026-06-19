"""CSRF token fetch-and-cache for OData v4 mutating requests."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import requests as _requests

from sap_cloud_sdk.core.odata._constants import (
    CSRF_FETCH_TIMEOUT,
    CSRF_FETCH_VALUE,
    CSRF_HEADER,
)
from sap_cloud_sdk.core.odata.exceptions import ODataCsrfError

if TYPE_CHECKING:
    from ._transport import ODataHttpTransport


class CsrfTokenProvider:
    """Fetch and cache a CSRF token for one OData service root.

    The token is fetched lazily on the first mutating request and cached
    until it is invalidated (typically after a 403 response).

    Thread-safe: internal state is protected by a :class:`threading.Lock`.

    Args:
        transport: The owning :class:`ODataHttpTransport` whose session and
            base URL are used to perform the CSRF-fetch GET.
    """

    def __init__(self, transport: "ODataHttpTransport") -> None:
        self._transport = transport
        self._token: str | None = None
        self._lock = threading.Lock()

    def get(self) -> str:
        """Return the cached CSRF token, fetching from the service if needed."""
        with self._lock:
            if self._token is not None:
                return self._token

        token = self._fetch()
        with self._lock:
            if self._token is None:
                self._token = token
            return self._token

    def invalidate(self) -> None:
        """Discard the cached token so the next call re-fetches."""
        with self._lock:
            self._token = None

    def _fetch(self) -> str:
        url = self._transport._base_url + "/"
        try:
            resp = self._transport._session.get(
                url,
                headers={CSRF_HEADER: CSRF_FETCH_VALUE},
                timeout=CSRF_FETCH_TIMEOUT,
            )
        except _requests.RequestException as exc:
            raise ODataCsrfError(f"CSRF fetch failed: {exc}") from exc

        token = resp.headers.get(CSRF_HEADER, "")
        if not token:
            raise ODataCsrfError(
                f"Service did not return a CSRF token (HTTP {resp.status_code})"
            )
        return token
