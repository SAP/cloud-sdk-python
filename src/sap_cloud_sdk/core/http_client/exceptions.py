"""HTTP client exception hierarchy."""

from __future__ import annotations

from typing import Any


class HttpClientError(Exception):
    """Base for all HTTP client errors."""


class HttpResponseError(HttpClientError):
    """Non-2xx HTTP response received from the target system."""

    def __init__(self, response: Any) -> None:
        self.status_code: int = response.status_code
        self.response = response
        super().__init__(f"HTTP {response.status_code}: {response.url}")


class HttpNotFoundError(HttpResponseError):
    """Resource not found (HTTP 404)."""


class HttpUnauthorizedError(HttpResponseError):
    """Authentication or authorisation failure (HTTP 401/403)."""


class HttpConnectionError(HttpClientError):
    """Network-level failure — no HTTP response was received."""
