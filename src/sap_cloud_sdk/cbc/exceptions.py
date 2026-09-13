"""Exception classes for the CBC (Central Business Configuration) module."""

from __future__ import annotations

from dataclasses import dataclass


class CBCError(Exception):
    """Base exception for all CBC module errors."""

    pass


class CBCConfigError(CBCError):
    """Raised when CBC configuration is missing or unusable.

    Raised when no configuration can be resolved from the environment, or when
    configuration is partially set (e.g. only one of the cert/key env vars is
    provided, or a path env var points to a non-existent file).
    """

    pass


@dataclass(frozen=True)
class HttpContext:
    """Context attached to HTTP exceptions.

    Attributes:
        status_code: HTTP status code, or ``-1`` for network-level failures.
        request_method: HTTP verb (GET, POST, PATCH, …).
        request_url: Full request URL.
    """

    status_code: int
    request_method: str
    request_url: str


class CBCHttpError(CBCError):
    """Raised for HTTP errors communicating with the CBC service.

    Attributes:
        code: Application-level error code from the CBC API response, if available.
        http_context: Request/response context.
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        http_context: HttpContext | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_context = http_context

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.code:
            parts.append(f"code={self.code}")
        if self.http_context:
            parts.append(f"http_context={self.http_context}")
        return " | ".join(parts)


class CBCClientError(CBCHttpError):
    """Raised for 4xx responses from the CBC API."""

    pass


class CBCServerError(CBCHttpError):
    """Raised for 5xx responses from the CBC API."""

    pass


class CBCNetworkError(CBCError):
    """Raised for network-level failures (DNS, connection refused, timeouts)."""

    def __init__(
        self,
        message: str,
        http_context: HttpContext | None = None,
    ) -> None:
        super().__init__(message)
        self.http_context = http_context
