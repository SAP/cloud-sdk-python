"""SAP Cloud SDK for Python - Audit Log module

The create_client() function detects the environment:
- Cloud: Load credentials from mounts/env vars and points to an instance in the cloud

Usage:
    from cloud_sdk_python.core.auditlog import create_client, SecurityEvent
    
    # Auto-detection based on environment
    client = create_client()
    
    # Create and log events
    event = SecurityEvent(data="Login attempt", success=True)
    client.log(event)
"""
from typing import Optional

from cloud_sdk_python.core.telemetry import Module
from cloud_sdk_python.core.auditlog.client import AuditLogClient
from cloud_sdk_python.core.auditlog._http_transport import HttpTransport
from cloud_sdk_python.core.auditlog.models import (
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
    Tenant,
    FailedMessage,
    SecurityEventAttribute,
    DataAccessAttribute,
    ChangeAttribute,
    DeletedAttribute
)
from cloud_sdk_python.core.auditlog.config import (
    AuditLogConfig,
    _load_config_from_env
)
from cloud_sdk_python.core.auditlog.exceptions import (
    AuditLogError,
    ClientCreationError,
    TransportError,
)

def create_client(*, config: Optional[AuditLogConfig] = None, _telemetry_source: Optional[Module] = None) -> AuditLogClient:
    """Creates an AuditLogClient with automatic transport selection.
    
    Uses HTTP transport with OAuth2 authentication

    Args:
        config: Optional AuditLogConfig for custom configuration.
                If None, auto-detects environment and loads config.
        _telemetry_source: Internal parameter to track which SDK module created this client.
                           Should not be used by end users.
    
    Returns:
        AuditLogClient: Configured client ready for audit operations.
        
    Raises:
        ClientCreationError: If client creation fails due to configuration issues.
    """
    try:
        if config is not None:
            transport = HttpTransport(config)
            return AuditLogClient(transport, _telemetry_source=_telemetry_source)

        transport = HttpTransport(_load_config_from_env())
        return AuditLogClient(transport, _telemetry_source=_telemetry_source)

    except Exception as e:
        raise ClientCreationError(f"Failed to create audit log client: {e}")


__all__ = [
    # Client
    "AuditLogClient",
    # Public user-facing types
    "SecurityEvent",
    "DataAccessEvent",
    "DataModificationEvent", 
    "ConfigurationChangeEvent",
    "DataDeletionEvent",
    "ConfigurationDeletionEvent",
    "Tenant",
    "FailedMessage",
    "AuditLogConfig",
    # Attribute types
    "SecurityEventAttribute",
    "DataAccessAttribute", 
    "ChangeAttribute",
    "DeletedAttribute",
    # Factory function
    "create_client",
    # Exceptions
    "AuditLogError",
    "ClientCreationError",
    "TransportError",
]
