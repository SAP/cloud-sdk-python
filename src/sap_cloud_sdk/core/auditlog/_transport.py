"""Transport layer abstraction for audit log messages."""

from abc import ABC, abstractmethod
from typing import Union

from sap_cloud_sdk.core.auditlog.models import (
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
)

AuditMessage = Union[
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
]


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

    def close(self) -> None:
        """Close the transport and release resources.

        Default implementation is a no-op. Subclasses may override
        to perform cleanup (e.g., closing HTTP sessions).
        """
        pass
