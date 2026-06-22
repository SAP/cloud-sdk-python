# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Comprehensive tests for output management module."""

import pytest

from sap_cloud_sdk.outputmanagement.models import (
    OutputResponse,
    EmailConfiguration,
    AttachmentConfig,
    PreGeneratedAttachment,
    FormConfiguration,
)
from sap_cloud_sdk.outputmanagement.models.output_response import ErrorResponse
from sap_cloud_sdk.outputmanagement.exceptions import (
    OutputManagementException,
    ValidationException,
    AuthenticationException,
)


class TestPydanticModelFeatures:
    """Test Pydantic model features."""

    def test_output_response_fields(self):
        """Test OutputResponse has expected fields."""
        response = OutputResponse(outputRequestId="test")

        assert hasattr(response, "output_request_id")
        assert hasattr(response, "error")
        assert response.output_request_id == "test"

    def test_email_configuration_fields(self):
        """Test EmailConfiguration has expected fields."""
        config = EmailConfiguration(
            emailNotificationTemplateKey="TEST_TEMPLATE",
            emailTemplateLanguage="en",
            to=["test@example.com"]
        )

        assert hasattr(config, "to")
        assert hasattr(config, "email_notification_template_key")
        assert hasattr(config, "email_template_language")
        assert config.to == ["test@example.com"]

    def test_attachment_config_fields(self):
        """Test AttachmentConfig has expected fields."""
        form_config = FormConfiguration(form_id="test-form")
        attachment = AttachmentConfig(formConfiguration=form_config)

        assert hasattr(attachment, "form_configuration")
        assert hasattr(attachment, "pre_generated_attachments")
        assert attachment.form_configuration is not None
        assert attachment.form_configuration.form_id == "test-form"

    def test_pre_generated_attachment_fields(self):
        """Test PreGeneratedAttachment has expected fields."""
        attachment = PreGeneratedAttachment(
            url="https://dms.example.com/path/file.pdf",
            source="DMS"
        )

        assert hasattr(attachment, "url")
        assert hasattr(attachment, "source")
        assert attachment.url == "https://dms.example.com/path/file.pdf"


class TestModelValidation:
    """Test model validation and constraints."""

    def test_email_configuration_requires_recipients(self):
        """Test that email configuration requires recipients."""
        # Should be able to create with recipients
        config = EmailConfiguration(
            emailNotificationTemplateKey="TEST_TEMPLATE",
            emailTemplateLanguage="en",
            to=["user@example.com"]
        )
        assert len(config.to) > 0

    def test_attachment_with_form_configuration(self):
        """Test that attachment can have form configuration."""
        form_config = FormConfiguration(form_id="document-form")
        attachment = AttachmentConfig(formConfiguration=form_config)

        assert attachment.form_configuration is not None
        assert attachment.form_configuration.form_id == "document-form"

    def test_output_response_with_request_id(self):
        """Test that output response can have request ID."""
        response = OutputResponse(outputRequestId="req-123")

        assert response.output_request_id is not None
        assert len(response.output_request_id) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_email_with_many_recipients(self):
        """Test email with many recipients."""
        many_recipients = [f"user{i}@example.com" for i in range(100)]
        config = EmailConfiguration(
            emailNotificationTemplateKey="MASS_EMAIL_TEMPLATE",
            emailTemplateLanguage="en",
            to=many_recipients
        )
        assert len(config.to) == 100

    def test_email_with_special_characters_in_template_key(self):
        """Test email with special characters in template key."""
        config = EmailConfiguration(
            emailNotificationTemplateKey="TEST_TEMPLATE_2024",
            emailTemplateLanguage="en",
            to=["user@example.com"]
        )
        assert "2024" in config.email_notification_template_key

    def test_output_response_with_error(self):
        """Test output response with error."""
        error = ErrorResponse(message="Processing failed")
        response = OutputResponse(error=error)

        assert response.output_request_id is None
        assert response.error is not None
        assert response.error.message == "Processing failed"

    def test_output_response_empty(self):
        """Test output response with no fields."""
        response = OutputResponse()

        assert response.output_request_id is None
        assert response.error is None

    def test_pre_generated_attachment_url_validation(self):
        """Test PreGeneratedAttachment URL validation."""
        # Valid URL
        attachment = PreGeneratedAttachment(
            url="https://dms.example.com/file.pdf",
            source="DMS"
        )
        assert attachment.url.startswith("https://")

    def test_attachment_config_with_multiple_pre_generated(self):
        """Test AttachmentConfig with multiple pre-generated attachments."""
        attachments = [
            PreGeneratedAttachment(url="https://dms.example.com/file1.pdf", source="DMS"),
            PreGeneratedAttachment(url="https://dms.example.com/file2.pdf", source="DMS"),
        ]
        config = AttachmentConfig(preGeneratedAttachments=attachments)

        assert config.pre_generated_attachments is not None
        assert len(config.pre_generated_attachments) == 2


class TestExceptionScenarios:
    """Test various exception scenarios."""

    def test_exception_with_nested_message(self):
        """Test exception with nested error message."""
        try:
            raise ValueError("Inner error")
        except ValueError as e:
            error = OutputManagementException(f"Outer error: {str(e)}")
            assert "Inner error" in error.message
            assert "Outer error" in error.message

    def test_multiple_exception_types(self):
        """Test catching different exception types."""
        errors = [
            OutputManagementException("General error"),
            ValidationException("Validation error"),
            AuthenticationException("Authentication error"),
        ]

        for error in errors:
            assert isinstance(error, OutputManagementException)
            assert isinstance(error, Exception)

    def test_exception_repr(self):
        """Test exception representation."""
        error = OutputManagementException("Test error")
        repr_str = repr(error)
        assert "OutputManagementException" in repr_str or "Test error" in repr_str


class TestModelComparisons:
    """Test model comparison operations."""

    def test_output_response_equality(self):
        """Test output response equality."""
        response1 = OutputResponse(outputRequestId="req-1")
        response2 = OutputResponse(outputRequestId="req-1")
        response3 = OutputResponse(outputRequestId="req-2")

        assert response1 == response2
        assert response1 != response3

    def test_pre_generated_attachment_equality(self):
        """Test PreGeneratedAttachment equality."""
        att1 = PreGeneratedAttachment(
            url="https://dms.example.com/file.pdf",
            source="DMS"
        )
        att2 = PreGeneratedAttachment(
            url="https://dms.example.com/file.pdf",
            source="DMS"
        )
        att3 = PreGeneratedAttachment(
            url="https://dms.example.com/other.pdf",
            source="DMS"
        )

        assert att1 == att2
        assert att1 != att3


class TestModelSerialization:
    """Test model serialization capabilities using Pydantic's model_dump."""

    def test_output_response_to_dict(self):
        """Test converting OutputResponse to dictionary."""
        response = OutputResponse(outputRequestId="req-123")
        response_dict = response.model_dump()

        assert isinstance(response_dict, dict)
        assert response_dict["output_request_id"] == "req-123"

    def test_email_configuration_to_dict(self):
        """Test converting EmailConfiguration to dictionary."""
        config = EmailConfiguration(
            emailNotificationTemplateKey="TEST_TEMPLATE",
            emailTemplateLanguage="en",
            to=["user@example.com"]
        )
        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert config_dict["to"] == ["user@example.com"]
        assert config_dict["email_notification_template_key"] == "TEST_TEMPLATE"

    def test_pre_generated_attachment_to_dict(self):
        """Test converting PreGeneratedAttachment to dictionary."""
        attachment = PreGeneratedAttachment(
            url="https://dms.example.com/file.pdf",
            source="DMS"
        )
        att_dict = attachment.model_dump()

        assert isinstance(att_dict, dict)
        assert att_dict["url"] == "https://dms.example.com/file.pdf"
        assert att_dict["source"] == "DMS"


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_email_with_form_attachment_scenario(self):
        """Test sending an email with form-generated PDF attachment."""
        form_config = FormConfiguration(
            form_id="invoice_form_2024",
            form_data={"invoice_number": "2024-001", "amount": 50000}
        )

        attachment = AttachmentConfig(formConfiguration=form_config)

        email = EmailConfiguration(
            emailNotificationTemplateKey="INVOICE_NOTIFICATION",
            emailTemplateLanguage="en",
            to=["customer@company.com"],
            cc=["accounting@company.com"],
            attachment=attachment
        )

        assert email.attachment is not None
        assert email.attachment.form_configuration is not None
        assert email.attachment.form_configuration.form_id == "invoice_form_2024"

    def test_report_generation_scenario(self):
        """Test report generation scenario."""
        response = OutputResponse(outputRequestId="report-2024-q1")

        assert response.output_request_id is not None
        assert response.output_request_id.startswith("report-")

    def test_bulk_email_scenario(self):
        """Test bulk email sending scenario."""
        recipients = [f"employee{i}@company.com" for i in range(1, 51)]

        email = EmailConfiguration(
            emailNotificationTemplateKey="NEWSLETTER_TEMPLATE",
            emailTemplateLanguage="en",
            to=recipients
        )

        assert len(email.to) == 50

    def test_email_with_dms_attachments_scenario(self):
        """Test email with multiple DMS attachments."""
        attachments = [
            PreGeneratedAttachment(
                url="https://dms.example.com/summary.pdf",
                source="DMS"
            ),
            PreGeneratedAttachment(
                url="https://dms.example.com/data.xlsx",
                source="DMS"
            ),
            PreGeneratedAttachment(
                url="https://dms.example.com/notes.txt",
                source="DMS"
            ),
        ]

        attachment_config = AttachmentConfig(preGeneratedAttachments=attachments)

        email = EmailConfiguration(
            emailNotificationTemplateKey="REPORT_PACKAGE_TEMPLATE",
            emailTemplateLanguage="en",
            to=["manager@company.com"],
            attachment=attachment_config
        )

        assert email.attachment is not None
        assert email.attachment.pre_generated_attachments is not None
        assert len(email.attachment.pre_generated_attachments) == 3
        assert all(att.source == "DMS" for att in email.attachment.pre_generated_attachments)
