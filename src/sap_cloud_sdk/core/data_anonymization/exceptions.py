"""Custom exceptions for SAP Data Anonymization Service."""


class DataAnonymizationError(Exception):
    """Base exception for data anonymization operations."""

    pass


class ClientCreationError(DataAnonymizationError):
    """Raised when anonymization client creation fails."""

    pass


class TransportError(DataAnonymizationError):
    """Raised when transport operations fail."""

    pass


class AuthenticationError(DataAnonymizationError):
    """Raised when OAuth2 authentication fails."""

    pass
