"""Custom exception hierarchy for the Consent SDK."""


class ConsentSDKError(Exception):
    """Base exception for all Consent SDK errors."""

    def __init__(self, message: str, odata_error: dict | None = None) -> None:
        """Store the error message and optional OData error payload.

        Args:
            message: Human-readable error description.
            odata_error: Parsed OData ``error`` object from the response body,
                if available. Defaults to an empty dict when not provided.
        """
        super().__init__(message)
        self.odata_error = odata_error or {}


class ClientCreationError(ConsentSDKError):
    """Raised when the SDK client fails to initialize."""


class AuthenticationError(ConsentSDKError):
    """Raised on HTTP 401 - credentials are missing, expired, or rejected by the service."""


class AuthorizationError(ConsentSDKError):
    """Raised on HTTP 403 - the caller is authenticated but lacks permission for the operation."""


class ValidationError(ConsentSDKError):
    """Raised when request input fails server-side validation."""


class NotFoundError(ConsentSDKError):
    """Raised when the requested resource does not exist."""


class ConflictError(ConsentSDKError):
    """Raised when the operation conflicts with existing state (e.g. duplicate name)."""


class ODataError(ConsentSDKError):
    """Raised for unexpected OData service error responses (any status not covered by a subclass)."""

    def __init__(
        self, message: str, status_code: int, odata_error: dict | None = None
    ) -> None:
        """Store the HTTP status code alongside the OData error payload.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code returned by the service.
            odata_error: Parsed OData ``error`` object from the response body,
                if available.
        """
        super().__init__(message, odata_error)
        self.status_code = status_code
