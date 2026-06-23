"""Exception classes for the ADMS (Advanced Document Management Service) module."""

from __future__ import annotations


class AdmsError(Exception):
    """Base exception for all ADMS module errors."""

    pass


class ClientCreationError(AdmsError):
    """Raised when ADMS client creation fails (configuration or auth setup)."""

    pass


class ConfigError(AdmsError):
    """Raised when service binding configuration is missing or invalid."""

    pass


class HttpError(AdmsError):
    """Raised for HTTP-related errors communicating with the ADMS service.

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


class AdmsOperationError(AdmsError):
    """Raised when an ADMS API operation (CRUD, action, function) fails."""

    pass


class DocumentNotFoundError(AdmsOperationError):
    """Raised when a requested Document or DocumentRelation is not found (HTTP 404)."""

    pass


class ScanNotCleanError(AdmsOperationError):
    """Raised when a download is attempted on a document that is not in CLEAN scan state.

    This is a security gate — downloads are only allowed once the virus scanner
    has confirmed the file is clean.  Possible scan states that trigger this:
      - PENDING: scan in progress, retry later.
      - QUARANTINED: virus detected, access permanently blocked.
      - FAILED: scan infrastructure failure.
      - FILE_EXT_RESTRICTED: blocked by the tenant's file extension policy.
    """

    pass


class AuthError(AdmsError):
    """Raised when IAS token acquisition or exchange fails."""

    pass
