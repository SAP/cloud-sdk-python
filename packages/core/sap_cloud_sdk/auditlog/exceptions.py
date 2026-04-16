"""Custom exceptions for SAP Audit Log Service."""


class AuditLogError(Exception):
    """Base exception for audit log operations."""

    pass


class ClientCreationError(AuditLogError):
    """Raised when audit log client creation fails."""

    pass


class TransportError(AuditLogError):
    """Raised when transport operations fail."""

    pass


class AuthenticationError(AuditLogError):
    """Raised when OAuth2 authentication fails."""

    pass
