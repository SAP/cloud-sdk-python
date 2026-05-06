"""Unit tests for the data anonymization client."""

from unittest.mock import MagicMock
from unittest.mock import patch

from sap_cloud_sdk.core.data_anonymization.client import DataAnonymizationClient
from sap_cloud_sdk.core.data_anonymization.models import (
    AnonymizeFileRequest,
    AnonymizeResult,
    AnonymizeTextRequest,
    FileOperationResult,
    PseudonymizeFileRequest,
    PseudonymizeResult,
    PseudonymizeTextRequest,
)
from sap_cloud_sdk.core.telemetry import Module, Operation


class TestDataAnonymizationClient:
    def test_anonymize_text_calls_transport(self) -> None:
        transport = MagicMock()
        transport.anonymize_text.return_value = AnonymizeResult(result="anon")
        client = DataAnonymizationClient(transport)
        request = AnonymizeTextRequest(text="John Doe")

        result = client.anonymize_text(request)

        assert result.result == "anon"
        transport.anonymize_text.assert_called_once_with(request)

    def test_anonymize_file_calls_transport(self) -> None:
        transport = MagicMock()
        transport.anonymize_file.return_value = FileOperationResult(job_id="job-1")
        client = DataAnonymizationClient(transport)
        request = AnonymizeFileRequest(file_content=b"hello", file_name="sample.txt")

        result = client.anonymize_file(request)

        assert result.job_id == "job-1"
        transport.anonymize_file.assert_called_once_with(request)

    def test_pseudonymize_text_calls_transport(self) -> None:
        transport = MagicMock()
        transport.pseudonymize_text.return_value = PseudonymizeResult(result="pseudo")
        client = DataAnonymizationClient(transport)
        request = PseudonymizeTextRequest(text="John Doe")

        result = client.pseudonymize_text(request)

        assert result.result == "pseudo"
        transport.pseudonymize_text.assert_called_once_with(request)

    def test_pseudonymize_file_calls_transport(self) -> None:
        transport = MagicMock()
        transport.pseudonymize_file.return_value = FileOperationResult(
            content=b"zip-bytes"
        )
        client = DataAnonymizationClient(transport)
        request = PseudonymizeFileRequest(
            file_content=b"{}",
            file_name="sample.json",
            pseudonymization_secret="12345678901234567890123456789012",
        )

        result = client.pseudonymize_file(request)

        assert result.content == b"zip-bytes"
        transport.pseudonymize_file.assert_called_once_with(request)

    def test_alias_methods_delegate_to_text_operations(self) -> None:
        transport = MagicMock()
        transport.anonymize_text.return_value = AnonymizeResult(result="anon")
        transport.pseudonymize_text.return_value = PseudonymizeResult(result="pseudo")
        client = DataAnonymizationClient(transport)

        anonymize_result = client.anonymize(AnonymizeTextRequest(text="hello"))
        pseudonymize_result = client.pseudonymize(PseudonymizeTextRequest(text="hello"))

        assert anonymize_result.result == "anon"
        assert pseudonymize_result.result == "pseudo"

    def test_invalid_request_does_not_call_transport(self) -> None:
        transport = MagicMock()
        client = DataAnonymizationClient(transport)

        try:
            client.anonymize_text(AnonymizeTextRequest(text="   "))
        except ValueError as error:
            assert "text must not be empty" in str(error)
        else:
            raise AssertionError("Expected ValueError to be raised")

        transport.anonymize_text.assert_not_called()

    def test_close_delegates_to_transport(self) -> None:
        transport = MagicMock()
        client = DataAnonymizationClient(transport)

        client.close()

        transport.close.assert_called_once_with()

    def test_init_wraps_assignment_errors(self, monkeypatch) -> None:
        original_setattr = DataAnonymizationClient.__setattr__

        def fail_setattr(self, name, value):
            if name == "_transport":
                raise RuntimeError("boom")
            return original_setattr(self, name, value)

        monkeypatch.setattr(DataAnonymizationClient, "__setattr__", fail_setattr)

        try:
            DataAnonymizationClient(MagicMock())
        except Exception as error:  # noqa: BLE001
            assert "Failed to create DataAnonymizationClient" in str(error)
        else:
            raise AssertionError("Expected client creation to fail")

    def test_context_manager_closes_transport(self) -> None:
        transport = MagicMock()

        with DataAnonymizationClient(transport) as client:
            assert client is not None

        transport.close.assert_called_once_with()

    def test_anonymize_text_records_request_metric_without_payload(self) -> None:
        transport = MagicMock()
        transport.anonymize_text.return_value = AnonymizeResult(result="anon")
        client = DataAnonymizationClient(transport)
        request = AnonymizeTextRequest(text="John Doe")

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
        ) as mock_metric:
            client.anonymize_text(request)

        mock_metric.assert_called_once_with(
            Module.DATA_ANONYMIZATION,
            None,
            Operation.DATA_ANONYMIZATION_ANONYMIZE_TEXT,
            False,
        )
        assert "John Doe" not in str(mock_metric.call_args)

    def test_pseudonymize_text_records_error_metric_without_payload(self) -> None:
        transport = MagicMock()
        transport.pseudonymize_text.side_effect = RuntimeError("boom")
        client = DataAnonymizationClient(transport)
        request = PseudonymizeTextRequest(text="John Doe")

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_error_metric"
        ) as mock_metric:
            try:
                client.pseudonymize_text(request)
            except RuntimeError as error:
                assert str(error) == "boom"
            else:
                raise AssertionError("Expected RuntimeError to be raised")

        mock_metric.assert_called_once_with(
            Module.DATA_ANONYMIZATION,
            None,
            Operation.DATA_ANONYMIZATION_PSEUDONYMIZE_TEXT,
            False,
        )
        assert "John Doe" not in str(mock_metric.call_args)
