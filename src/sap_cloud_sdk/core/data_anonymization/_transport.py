"""Transport layer abstraction for the Data Anonymization Service."""

from abc import ABC, abstractmethod

from sap_cloud_sdk.core.data_anonymization.models import (
    AnonymizeFileRequest,
    AnonymizeRequest,
    AnonymizeResult,
    FileOperationResult,
    PseudonymizeFileRequest,
    PseudonymizeRequest,
    PseudonymizeResult,
)


class Transport(ABC):
    """Abstract base class for anonymization transport implementations."""

    @abstractmethod
    def anonymize_text(self, request: AnonymizeRequest) -> AnonymizeResult:
        """Send a text anonymization request and return the result.

        Args:
            request: Populated AnonymizeRequest.

        Raises:
            TransportError: If the transport operation fails.
        """

    @abstractmethod
    def anonymize_file(self, request: AnonymizeFileRequest) -> FileOperationResult:
        """Send a file anonymization request and return the result.

        Args:
            request: Populated `AnonymizeFileRequest`.

        Raises:
            TransportError: If the transport operation fails.
        """

    @abstractmethod
    def pseudonymize_text(self, request: PseudonymizeRequest) -> PseudonymizeResult:
        """Send a text pseudonymization request and return the result.

        Args:
            request: Populated PseudonymizeRequest.

        Raises:
            TransportError: If the transport operation fails.
        """

    @abstractmethod
    def pseudonymize_file(
        self,
        request: PseudonymizeFileRequest,
    ) -> FileOperationResult:
        """Send a file pseudonymization request and return the result.

        Args:
            request: Populated `PseudonymizeFileRequest`.

        Raises:
            TransportError: If the transport operation fails.
        """

    def anonymize(self, request: AnonymizeRequest) -> AnonymizeResult:
        """Backward-compatible alias for `anonymize_text()`."""
        return self.anonymize_text(request)

    def pseudonymize(self, request: PseudonymizeRequest) -> PseudonymizeResult:
        """Backward-compatible alias for `pseudonymize_text()`."""
        return self.pseudonymize_text(request)

    def close(self) -> None:
        """Close the transport and release resources.

        Default is a no-op; subclasses may override for cleanup.
        """
