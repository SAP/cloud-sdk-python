"""Exception classes for the ADMS (Advanced Document Management Service) module."""

from __future__ import annotations

from sap_cloud_sdk.core.odata.exceptions import (
    ODataNotFoundError as DocumentNotFoundError,
    ODataRequestError as HttpError,
)

__all__ = [
    "AdmsError",
    "AdmsOperationError",
    "AuthError",
    "ClientCreationError",
    "ConfigError",
    "DocumentNotFoundError",
    "HttpError",
    "ScanNotCleanError",
]


class AdmsError(Exception):
    """Base exception for all ADMS module errors."""

    pass


class ClientCreationError(AdmsError):
    """Raised when ADMS client creation fails (configuration or auth setup)."""

    pass


class ConfigError(AdmsError):
    """Raised when service binding configuration is missing or invalid."""

    pass


class AdmsOperationError(AdmsError):
    """Raised when an ADMS API operation (CRUD, action, function) fails."""

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
