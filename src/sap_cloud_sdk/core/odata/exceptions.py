"""OData-specific exception hierarchy."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import requests


class ODataError(Exception):
    """Base for all OData-related errors."""


class ODataRequestError(ODataError):
    """HTTP-level error from an OData service (non-2xx response)."""

    def __init__(self, response: "requests.Response") -> None:
        self.status_code = response.status_code
        self.response = response
        try:
            body = response.json()
            err = body.get("error") or {}
            detail = err.get("message") or err.get("code")
        except Exception:
            detail = None
        suffix = f" — {detail}" if detail else ""
        super().__init__(f"OData request failed: HTTP {response.status_code}{suffix}")


class ODataNotFoundError(ODataRequestError):
    """Entity not found (HTTP 404)."""


class ODataAuthError(ODataRequestError):
    """Authentication or authorization failure (HTTP 401/403)."""


class ODataDeserializationError(ODataError):
    """Failed to deserialize an OData response payload."""


class ODataCsrfError(ODataError):
    """Failed to fetch or validate a CSRF token."""
