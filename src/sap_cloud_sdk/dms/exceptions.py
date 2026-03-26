import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DMSError(Exception):
    """Base exception for all DMS errors."""
    def __init__(self, message: Optional[str] = None, status_code: Optional[int] = None, error_content: str = "") -> None:
        self.status_code = status_code
        self.error_content = error_content
        super().__init__(message)


class DMSObjectNotFoundException(DMSError):
    """The specified repository or resource does not exist."""

class DMSPermissionDeniedException(DMSError):
    """Access token is invalid, expired, or lacks required permissions."""

class DMSInvalidArgumentException(DMSError):
    """The request payload contains invalid or disallowed parameters."""

class DMSConnectionError(DMSError):
    """A network or connection failure occurred."""

class DMSRuntimeException(DMSError):
    """Unexpected server-side error."""