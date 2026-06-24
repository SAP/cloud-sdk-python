"""Custom exception hierarchy for the Consent SDK."""


class ConsentSDKError(Exception):
    """Base exception for all Consent SDK errors."""

    def __init__(self, message: str, odata_error: dict | None = None) -> None:
        """Store the OData error payload alongside the human-readable message."""
        super().__init__(message)
        self.odata_error = odata_error or {}


class ClientCreationError(ConsentSDKError):
    """Raised when the SDK client fails to initialize."""


class AuthenticationError(ConsentSDKError):
    """Raised when the bearer token is missing or rejected."""


class AuthorizationError(ConsentSDKError):
    """Raised when the caller lacks the required OData role."""


class ValidationError(ConsentSDKError):
    """Raised when request input fails server-side validation."""


class NotFoundError(ConsentSDKError):
    """Raised when the requested resource does not exist."""


class ConflictError(ConsentSDKError):
    """Raised when the operation conflicts with existing state (e.g. duplicate name)."""


class ODataError(ConsentSDKError):
    """Raised for unexpected OData service error responses."""

    def __init__(
        self, message: str, status_code: int, odata_error: dict | None = None
    ) -> None:
        """Store the HTTP status code alongside the OData error payload."""
        super().__init__(message, odata_error)
        self.status_code = status_code
