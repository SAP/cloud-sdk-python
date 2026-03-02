"""Audit log client implementation."""

from typing import List, Optional

from cloud_sdk_python.core.auditlog.models import (
    FailedMessage
)
from cloud_sdk_python.core.auditlog._transport import Transport, AuditMessage
from cloud_sdk_python.core.auditlog.exceptions import ClientCreationError
from cloud_sdk_python.core.telemetry import Module, Operation, record_metrics


class AuditLogClient:
    """Client for SAP Audit Log Service operations.
    
    This class provides methods for logging audit events to the SAP Audit Log Service.
    It supports both single event logging and batch operations.
    
    Note:
        Do not instantiate this class directly. Use the create_client() factory function
        instead, which handles environment detection and proper transport configuration.
        
    Example:
        ```python
        from cloud_sdk_python.core.auditlog import create_client, SecurityEvent
        
        # Correct way - use factory function
        client = create_client()
        
        # Log an event
        event = SecurityEvent(data="User login", success=True)
        client.log(event)
        ```
    """
    
    def __init__(self, transport: Transport, _telemetry_source: Optional[Module] = None):
        """Initialize audit log client with dependency injection.
        
        Warning:
            This constructor is for internal use only. Use create_client() instead
            to create AuditLogClient instances. Direct instantiation bypasses proper
            environment detection and configuration.
        
        Args:
            transport: Transport implementation to use.
            _telemetry_source: Internal parameter to track which SDK module created this client.
                              None means created by user code (default).

        Raises:
            ClientCreationError: If client creation fails.
        """
        try:
            self._transport = transport
            self._telemetry_source = _telemetry_source
        except Exception as e:
            raise ClientCreationError(f"Failed to create audit log client: {e}")
    
    @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
    def log(self, event: AuditMessage) -> None:
        """Log a single audit event.
        
        Args:
            event: The audit event to log.
            
        Raises:
            ValidationError: If event validation fails.
            TransportError: If transport operation fails.
        """
        event.validate()
        self._transport.send(event)
    
    @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG_BATCH)
    def log_batch(self, events: List[AuditMessage]) -> List[FailedMessage]:
        """Log multiple audit events in batch.
        
        Args:
            events: List of audit events to log.
            
        Returns:
            List of events that failed to be logged.
        """
        failed = []
        
        for event in events:
            try:
                event.validate()
                self._transport.send(event)
            except Exception as e:
                failed.append(FailedMessage(message=event, error=str(e)))
        
        return failed

    def close(self) -> None:
        """Close the client and cleanup resources."""
        if hasattr(self._transport, 'close'):
            self._transport.close()
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and cleanup resources."""
        self.close()
