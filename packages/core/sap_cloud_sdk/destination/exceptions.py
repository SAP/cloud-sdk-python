"""Exception classes for the Destination module."""


class DestinationError(Exception):
    """Base exception for all Destination module errors."""

    pass


class ClientCreationError(DestinationError):
    """Raised when Destination client creation fails."""

    pass


class ConfigError(DestinationError):
    """Raised when configuration or secret resolution fails."""

    pass


class HttpError(DestinationError):
    """Raised for HTTP-related errors from Destination Service.

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


class DestinationOperationError(DestinationError):
    """Raised when a Destination operation (get/list/create/update/delete) fails."""

    pass


class DestinationNotFoundError(DestinationOperationError):
    """Raised when a requested Destination is not found (HTTP 404)."""

    pass
