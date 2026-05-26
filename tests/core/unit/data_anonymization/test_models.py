"""Unit tests for cloud SDK data anonymization models."""

from sap_cloud_sdk.core.data_anonymization.models import (
    AnonymizeFileRequest,
    AnonymizeFileResult,
    AnonymizeRequest,
    AnonymizeResult,
    AnonymizeTextRequest,
    EntityMapping,
    FileOperationResult,
    PseudonymizeFileResult,
    PseudonymizeFileRequest,
    PseudonymizeRequest,
    PseudonymizeResult,
    PseudonymizeTextRequest,
)


def assert_raises(exception_type, match, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exception_type as error:
        assert match in str(error)
        return error
    raise AssertionError(f"Expected {exception_type.__name__} to be raised")


class TestTextRequests:
    def test_anonymize_text_request_to_form_fields(self) -> None:
        request = AnonymizeTextRequest(
            text="John Doe",
            entities=["profile-person", "profile-email"],
            anonymization_method_per_profile='[{"profile-person":"_remove_"}]',
            allowlist="allowed@example.com",
            enable_default_allowlist=False,
            custom_entities='{"custom-id":"ID-[0-9]+"}'
        )

        request.validate()

        assert request.to_form_fields() == [
            ("text", "John Doe"),
            ("entities", "profile-person"),
            ("entities", "profile-email"),
            (
                "anonymization-method-per-profile",
                '[{"profile-person":"_remove_"}]',
            ),
            ("whitelist", "allowed@example.com"),
            ("enable-default-whitelist", "false"),
            ("custom-entities", '{"custom-id":"ID-[0-9]+"}'),
        ]

    def test_anonymize_text_request_rejects_empty_text(self) -> None:
        request = AnonymizeTextRequest(text="   ")

        assert_raises(ValueError, "text must not be empty", request.validate)

    def test_pseudonymize_text_request_requires_long_secret(self) -> None:
        request = PseudonymizeTextRequest(
            text="John Doe",
            pseudonymization_secret="short",
        )

        assert_raises(ValueError, "at least 32 characters", request.validate)

    def test_text_request_rejects_invalid_entities(self) -> None:
        request = AnonymizeTextRequest(
            text="John Doe",
            entities=["profile-person", ""]
        )

        assert_raises(ValueError, "entities must be a list", request.validate)

    def test_text_request_aliases(self) -> None:
        assert AnonymizeRequest is AnonymizeTextRequest
        assert PseudonymizeRequest is PseudonymizeTextRequest


class TestFileRequests:
    def test_anonymize_file_request_accepts_file_path(self) -> None:
        request = AnonymizeFileRequest(
            file_path="/tmp/sample.pdf",
            entities=["profile-person"],
        )

        request.validate()

        assert request.to_form_fields() == [("entities", "profile-person")]
        assert request.resolved_file_name() == "sample.pdf"

    def test_anonymize_file_request_accepts_file_content(self) -> None:
        request = AnonymizeFileRequest(
            file_content=b"hello",
            file_name="sample.txt"
        )

        request.validate()

        assert request.resolved_file_name() == "sample.txt"

    def test_file_request_requires_exactly_one_source(self) -> None:
        assert_raises(
            ValueError,
            "exactly one of file_path or file_content",
            AnonymizeFileRequest().validate,
        )

        assert_raises(
            ValueError,
            "exactly one of file_path or file_content",
            AnonymizeFileRequest(
                file_path="sample.txt",
                file_content=b"hello",
            ).validate,
        )

    def test_pseudonymize_file_request_form_fields(self) -> None:
        request = PseudonymizeFileRequest(
            file_content=b"{}",
            file_name="sample.json",
            pseudonymization_metadata='{"batch":"1"}',
            pseudonymization_secret="12345678901234567890123456789012",
        )

        request.validate()

        assert request.to_form_fields() == [
            ("pseudonymization-metadata", '{"batch":"1"}'),
            ("pseudonymization-secret", "12345678901234567890123456789012"),
        ]

    def test_pseudonymize_file_request_defaults_file_name(self) -> None:
        request = PseudonymizeFileRequest(
            file_content=b"{}",
            pseudonymization_secret="12345678901234567890123456789012",
        )

        request.validate()

        assert request.resolved_file_name() == "upload.zip"

    def test_anonymize_file_request_defaults_file_name(self) -> None:
        request = AnonymizeFileRequest(file_content=b"hello")

        request.validate()

        assert request.resolved_file_name() == "upload.bin"


class TestResults:
    def test_anonymize_result_from_dict(self) -> None:
        result = AnonymizeResult.from_dict({"result": "<person>"})

        assert result.result == "<person>"
        assert result.raw == {"result": "<person>"}

    def test_entity_mapping_from_dict(self) -> None:
        mapping = EntityMapping.from_dict(
            {
                "original": "John Doe",
                "pseudonym": "TOKEN-1",
                "entityType": "PERSON",
            }
        )

        assert mapping.original == "John Doe"
        assert mapping.pseudonym == "TOKEN-1"
        assert mapping.entity_type == "PERSON"

    def test_pseudonymize_result_from_dict(self) -> None:
        result = PseudonymizeResult.from_dict(
            {
                "result": "TOKEN-1",
                "metadata": [
                    {
                        "original": "John Doe",
                        "pseudonym": "TOKEN-1",
                        "entity_type": "PERSON",
                    }
                ],
            }
        )

        assert result.result == "TOKEN-1"
        assert len(result.metadata) == 1
        assert result.metadata[0].entity_type == "PERSON"

    def test_pseudonymize_result_filters_non_dict_metadata(self) -> None:
        result = PseudonymizeResult.from_dict(
            {"result": "TOKEN-1", "metadata": ["skip", {"original": "John"}]}
        )

        assert len(result.metadata) == 1
        assert result.metadata[0].original == "John"

    def test_file_operation_result_defaults(self) -> None:
        result = FileOperationResult()

        assert result.result is None
        assert result.job_id is None
        assert result.content is None
        assert result.raw == {}

    def test_file_result_aliases(self) -> None:
        assert AnonymizeFileResult is FileOperationResult
        assert PseudonymizeFileResult is FileOperationResult
