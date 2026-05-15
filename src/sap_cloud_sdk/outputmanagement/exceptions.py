"""Exception classes for the Output Management SDK."""

from typing import Optional, Dict, Any


class OutputManagementException(Exception):
    """Base exception for Output Management SDK."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize exception.

        Args:
            message: Error message
            error_code: Error code
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation."""
        parts = [self.message]
        if self.error_code:
            parts.append(f"Error Code: {self.error_code}")
        if self.status_code:
            parts.append(f"Status Code: {self.status_code}")
        return " | ".join(parts)



class AuthenticationException(OutputManagementException):
    """Exception for authentication failures."""

    pass


class ValidationException(OutputManagementException):
    """Exception for validation failures."""

    pass


class NetworkException(OutputManagementException):
    """Exception for network-related errors."""

    pass


class DestinationNotFoundException(OutputManagementException):
    """Exception for destination not found errors."""

    pass


class DestinationAccessException(OutputManagementException):
    """Exception for destination access errors."""

    pass

