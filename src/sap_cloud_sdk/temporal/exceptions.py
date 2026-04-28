"""Custom exceptions for the SAP Cloud SDK Temporal module."""

from __future__ import annotations


class TemporalError(Exception):
    """Base exception for all Temporal module errors."""


class ConfigurationError(TemporalError):
    """Raised when required configuration is missing or invalid.

    Typical causes:
    - ``TEMPORAL_CALL_URL`` or ``TEMPORAL_NAMESPACE`` environment variables
      are not set and local-dev mode is not enabled.
    - No SPIFFE socket path could be discovered.
    """


class SpiffeError(TemporalError):
    """Raised when SPIFFE credential fetching fails."""

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.__cause__ = cause


class ClientCreationError(TemporalError):
    """Raised when the Temporal client cannot be created."""

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.__cause__ = cause


class WorkerCreationError(TemporalError):
    """Raised when the Temporal worker cannot be created."""

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.__cause__ = cause
