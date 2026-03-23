class DMSError(Exception):
    """Base exception for all DMS SDK errors."""


class HttpError(DMSError):
    """Raised for HTTP-related errors from the DMS service.

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
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text