"""Data Anonymization Service client."""

from types import TracebackType
from typing import Optional

from sap_cloud_sdk.core.data_anonymization._transport import Transport
from sap_cloud_sdk.core.data_anonymization.exceptions import ClientCreationError
from sap_cloud_sdk.core.data_anonymization.models import (
    AnonymizeFileRequest,
    AnonymizeRequest,
    AnonymizeResult,
    FileOperationResult,
    PseudonymizeFileRequest,
    PseudonymizeRequest,
    PseudonymizeResult,
)
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


class DataAnonymizationClient:
    """Client for SAP Data Anonymization Service operations.

    Do not instantiate directly — use the ``create_client()`` factory in
    ``data_anonymization`` which handles configuration
    loading and transport setup.

    Telemetry records operation-level metrics only. Request payloads,
    response payloads, and any other sensitive user data are never attached
    to telemetry attributes by this client.

    Example::

        from sap_cloud_sdk.core.data_anonymization import (
            create_client, AnonymizeRequest, PseudonymizeRequest,
        )

        client = create_client()

        result = client.anonymize(AnonymizeRequest(text="John Doe, john@example.com"))
        assert result.result is not None

        pseudo = client.pseudonymize(PseudonymizeRequest(text="John Doe"))
        assert pseudo.result is not None
        assert len(pseudo.metadata) >= 0
    """

    def __init__(
        self,
        transport: Transport,
        *,
        _telemetry_source: Optional[Module] = None,
    ) -> None:
        try:
            self._transport = transport
            self._telemetry_source = _telemetry_source
        except Exception as e:
            raise ClientCreationError(f"Failed to create DataAnonymizationClient: {e}")

    @record_metrics(
        Module.DATA_ANONYMIZATION,
        Operation.DATA_ANONYMIZATION_ANONYMIZE_TEXT,
    )
    def anonymize_text(self, request: AnonymizeRequest) -> AnonymizeResult:
        """Anonymize text, irreversibly replacing detected PII with placeholders.

        Args:
            request: Populated AnonymizeRequest.

        Returns:
            AnonymizeResult with the anonymized text.

        Raises:
            ValueError: If the request fails validation.
            TransportError: If the HTTP call fails.
        """
        request.validate()
        return self._transport.anonymize_text(request)

    @record_metrics(
        Module.DATA_ANONYMIZATION,
        Operation.DATA_ANONYMIZATION_ANONYMIZE_FILE,
    )
    def anonymize_file(self, request: AnonymizeFileRequest) -> FileOperationResult:
        """Anonymize a file using the multipart file endpoint.

        Args:
            request: Populated `AnonymizeFileRequest`.

        Returns:
            `FileOperationResult` containing either a text result, raw binary
            content, or additional response details in `raw`.
        """
        request.validate()
        return self._transport.anonymize_file(request)

    @record_metrics(
        Module.DATA_ANONYMIZATION,
        Operation.DATA_ANONYMIZATION_PSEUDONYMIZE_TEXT,
    )
    def pseudonymize_text(self, request: PseudonymizeRequest) -> PseudonymizeResult:
        """Pseudonymize text with a reversible token mapping.

        Args:
            request: Populated PseudonymizeRequest.

        Returns:
            PseudonymizeResult with the pseudonymized text and entity mappings.

        Raises:
            ValueError: If the request fails validation.
            TransportError: If the HTTP call fails.
        """
        request.validate()
        return self._transport.pseudonymize_text(request)

    @record_metrics(
        Module.DATA_ANONYMIZATION,
        Operation.DATA_ANONYMIZATION_PSEUDONYMIZE_FILE,
    )
    def pseudonymize_file(
        self,
        request: PseudonymizeFileRequest,
    ) -> FileOperationResult:
        """Pseudonymize a file using the multipart file endpoint.

        Args:
            request: Populated `PseudonymizeFileRequest`.

        Returns:
            `FileOperationResult` containing either a text result, ZIP/binary
            content, or additional response details in `raw`.
        """
        request.validate()
        return self._transport.pseudonymize_file(request)

    def anonymize(self, request: AnonymizeRequest) -> AnonymizeResult:
        """Backward-compatible alias for `anonymize_text()`."""
        return self.anonymize_text(request)

    def pseudonymize(self, request: PseudonymizeRequest) -> PseudonymizeResult:
        """Backward-compatible alias for `pseudonymize_text()`."""
        return self.pseudonymize_text(request)

    def close(self) -> None:
        """Close the client and release transport resources."""
        self._transport.close()

    def __enter__(self) -> "DataAnonymizationClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
