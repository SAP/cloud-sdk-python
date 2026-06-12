"""Exception classes for the Print module."""


class PrintError(Exception):
    """Base exception for all Print module errors."""

    pass


class ClientCreationError(PrintError):
    """Raised when Print client creation fails."""

    pass


class ConfigError(PrintError):
    """Raised when configuration or secret resolution fails."""

    pass


class HttpError(PrintError):
    """Raised for HTTP-related errors from Print Service.

    Attributes:
        status_code: HTTP status code returned by the service, if available.
        message: Human-readable error message.
        response_text: Raw response payload for diagnostics, if available.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class PrintOperationError(PrintError):
    """Raised when a Print operation fails."""

    pass
