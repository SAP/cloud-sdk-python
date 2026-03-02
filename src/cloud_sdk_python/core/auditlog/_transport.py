"""Transport layer abstraction for audit log messages."""

from abc import ABC, abstractmethod
from typing import Union

from cloud_sdk_python.core.auditlog.models import (
    SecurityEvent,
    DataAccessEvent, 
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent
)

AuditMessage = Union[SecurityEvent, DataAccessEvent, DataModificationEvent, ConfigurationChangeEvent, DataDeletionEvent, ConfigurationDeletionEvent]


class Transport(ABC):
    """Abstract base class for audit log transport implementations."""
    
    @abstractmethod
    def send(self, event: AuditMessage) -> None:
        """Send an audit event.
        
        Args:
            event: The audit event to send.
            
        Raises:
            TransportError: If the transport operation fails.
        """
        pass
