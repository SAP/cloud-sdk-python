"""Unit tests for the transport abstraction."""

from abc import ABC

from sap_cloud_sdk.core.data_anonymization._transport import Transport
from sap_cloud_sdk.core.data_anonymization.models import (
    AnonymizeFileRequest,
    AnonymizeResult,
    AnonymizeTextRequest,
    FileOperationResult,
    PseudonymizeFileRequest,
    PseudonymizeResult,
    PseudonymizeTextRequest,
)


class ConcreteTransport(Transport):
    def __init__(self) -> None:
        self.calls = []

    def anonymize_text(self, request: AnonymizeTextRequest) -> AnonymizeResult:
        self.calls.append(("anonymize_text", request))
        return AnonymizeResult(result="anon")

    def anonymize_file(self, request: AnonymizeFileRequest) -> FileOperationResult:
        self.calls.append(("anonymize_file", request))
        return FileOperationResult(result="anon-file")

    def pseudonymize_text(
        self,
        request: PseudonymizeTextRequest,
    ) -> PseudonymizeResult:
        self.calls.append(("pseudonymize_text", request))
        return PseudonymizeResult(result="pseudo")

    def pseudonymize_file(
        self,
        request: PseudonymizeFileRequest,
    ) -> FileOperationResult:
        self.calls.append(("pseudonymize_file", request))
        return FileOperationResult(result="pseudo-file")


class TestTransport:
    def test_is_abstract_base_class(self) -> None:
        assert issubclass(Transport, ABC)

        try:
            Transport()
        except TypeError:
            pass
        else:
            raise AssertionError("Transport() should not be instantiable")

    def test_alias_methods_delegate_to_text_operations(self) -> None:
        transport = ConcreteTransport()
        anonymize_request = AnonymizeTextRequest(text="hello")
        pseudonymize_request = PseudonymizeTextRequest(text="hello")

        anonymize_result = transport.anonymize(anonymize_request)
        pseudonymize_result = transport.pseudonymize(pseudonymize_request)

        assert anonymize_result.result == "anon"
        assert pseudonymize_result.result == "pseudo"
        assert transport.calls == [
            ("anonymize_text", anonymize_request),
            ("pseudonymize_text", pseudonymize_request),
        ]
