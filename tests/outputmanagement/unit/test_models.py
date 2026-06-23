# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for output management models."""

import pytest
from dataclasses import is_dataclass

from sap_cloud_sdk.outputmanagement import (
    OutputResponse,
    EmailConfiguration,
    AttachmentConfig,
    PreGeneratedAttachment,
    FormConfiguration,
)
from sap_cloud_sdk.outputmanagement._models import ErrorResponse


class TestOutputResponse:
    """Test OutputResponse model."""

    def test_output_response_is_dataclass(self):
        """Test that OutputResponse is a dataclass."""
        # OutputResponse is a Pydantic model, not a dataclass
        assert not is_dataclass(OutputResponse)

    def test_output_response_creation_basic(self):
        """Test creating a basic OutputResponse."""
        response = OutputResponse(
            outputRequestId="req-123"
        )
        assert response.output_request_id == "req-123"
        assert response.error is None

    def test_output_response_with_error(self):
        """Test OutputResponse with error."""
        error = ErrorResponse(
            message="Processing failed",
            code="ERR_001"
        )
        response = OutputResponse(error=error)

        assert response.output_request_id is None
        assert response.error is not None
        assert response.error.message == "Processing failed"
        assert response.error.code == "ERR_001"

    def test_output_response_equality(self):
        """Test OutputResponse equality."""
        response1 = OutputResponse(outputRequestId="req-1")
        response2 = OutputResponse(outputRequestId="req-1")
        response3 = OutputResponse(outputRequestId="req-2")

        assert response1 == response2
        assert response1 != response3

    def test_output_response_empty(self):
        """Test OutputResponse with no fields."""
        response = OutputResponse()

        assert response.output_request_id is None
        assert response.error is None


class TestEmailConfiguration:
    """Test EmailConfiguration model."""

    def test_email_configuration_is_dataclass(self):
        """Test that EmailConfiguration is a dataclass."""
        # EmailConfiguration is a Pydantic model, not a dataclass
        assert not is_dataclass(EmailConfiguration)

    def test_email_configuration_basic(self):
        """Test basic EmailConfiguration creation."""
        config = EmailConfiguration(
            emailNotificationTemplateKey="TEST_TEMPLATE",
            emailTemplateLanguage="en",
            to=["recipient@example.com"]
        )
        assert config.to == ["recipient@example.com"]
        assert config.email_notification_template_key == "TEST_TEMPLATE"
        assert config.email_template_language == "en"

    def test_email_configuration_with_cc_bcc(self):
        """Test EmailConfiguration with CC and BCC."""
        config = EmailConfiguration(
            emailNotificationTemplateKey="TEST_TEMPLATE",
            emailTemplateLanguage="en",
            to=["recipient@example.com"],
            cc=["cc@example.com"],
            bcc=["bcc@example.com"]
        )
        assert config.cc == ["cc@example.com"]
        assert config.bcc == ["bcc@example.com"]

    def test_email_configuration_multiple_recipients(self):
        """Test EmailConfiguration with multiple recipients."""
        config = EmailConfiguration(
            emailNotificationTemplateKey="MULTI_RECIPIENT_TEMPLATE",
            emailTemplateLanguage="en",
            to=["user1@example.com", "user2@example.com", "user3@example.com"]
        )
        assert len(config.to) == 3
        assert "user1@example.com" in config.to
        assert "user2@example.com" in config.to
        assert "user3@example.com" in config.to

    def test_email_configuration_with_attachment(self):
        """Test EmailConfiguration with attachment."""
        form_config = FormConfiguration(
            form_id="test-form-123"
        )
        attachment = AttachmentConfig(
            formConfiguration=form_config
        )
        config = EmailConfiguration(
            emailNotificationTemplateKey="TEST_TEMPLATE",
            emailTemplateLanguage="en",
            to=["recipient@example.com"],
            attachment=attachment
        )
        assert config.attachment is not None
        assert config.attachment.form_configuration is not None
        assert config.attachment.form_configuration.form_id == "test-form-123"

    def test_email_configuration_optional_fields(self):
        """Test EmailConfiguration with optional fields."""
        config = EmailConfiguration(
            emailNotificationTemplateKey="TEST_TEMPLATE",
            emailTemplateLanguage="en",
            to=["recipient@example.com"]
        )
        # Check that optional fields have appropriate defaults
        assert hasattr(config, 'cc')
        assert hasattr(config, 'bcc')
        assert hasattr(config, 'attachment')
        assert config.cc is None
        assert config.bcc is None
        assert config.attachment is None


class TestAttachmentConfig:
    """Test AttachmentConfig model."""

    def test_attachment_config_is_dataclass(self):
        """Test that AttachmentConfig is a dataclass."""
        # AttachmentConfig is a Pydantic model, not a dataclass
        assert not is_dataclass(AttachmentConfig)

    def test_attachment_config_with_form_configuration(self):
        """Test AttachmentConfig with form configuration."""
        form_config = FormConfiguration(form_id="test-form-123")
        attachment = AttachmentConfig(formConfiguration=form_config)

        assert attachment.form_configuration is not None
        assert attachment.form_configuration.form_id == "test-form-123"

    def test_attachment_config_with_pre_generated_attachments(self):
        """Test AttachmentConfig with pre-generated attachments."""
        pre_gen = PreGeneratedAttachment(
            url="https://dms.example.com/file.pdf",
            source="DMS"
        )
        attachment = AttachmentConfig(preGeneratedAttachments=[pre_gen])

        assert attachment.pre_generated_attachments is not None
        assert len(attachment.pre_generated_attachments) == 1
        assert attachment.pre_generated_attachments[0].url == "https://dms.example.com/file.pdf"

    def test_attachment_config_with_both(self):
        """Test AttachmentConfig with both form configuration and pre-generated attachments."""
        form_config = FormConfiguration(form_id="form-456")
        pre_gen = PreGeneratedAttachment(
            url="https://dms.example.com/doc.pdf",
            source="DMS"
        )
        attachment = AttachmentConfig(
            formConfiguration=form_config,
            preGeneratedAttachments=[pre_gen]
        )

        assert attachment.form_configuration is not None
        assert attachment.pre_generated_attachments is not None
        assert attachment.form_configuration.form_id == "form-456"
        assert len(attachment.pre_generated_attachments) == 1

    def test_attachment_config_empty(self):
        """Test AttachmentConfig with no configuration."""
        attachment = AttachmentConfig()

        assert attachment.form_configuration is None
        assert attachment.pre_generated_attachments is None


class TestPreGeneratedAttachment:
    """Test PreGeneratedAttachment model."""

    def test_pre_generated_attachment_is_dataclass(self):
        """Test that PreGeneratedAttachment is a dataclass."""
        # PreGeneratedAttachment is a Pydantic model, not a dataclass
        assert not is_dataclass(PreGeneratedAttachment)

    def test_pre_generated_attachment_basic(self):
        """Test basic PreGeneratedAttachment creation."""
        attachment = PreGeneratedAttachment(
            url="https://dms.example.com/attachments/report-123.pdf",
            source="DMS"
        )
        assert attachment.url == "https://dms.example.com/attachments/report-123.pdf"
        assert attachment.source == "DMS"

    def test_pre_generated_attachment_url_validation(self):
        """Test PreGeneratedAttachment URL validation."""
        # Valid HTTPS URL
        att1 = PreGeneratedAttachment(
            url="https://dms.example.com/file.pdf",
            source="DMS"
        )
        assert att1.url.startswith("https://")

        # Valid HTTP URL
        att2 = PreGeneratedAttachment(
            url="http://dms.example.com/file.pdf",
            source="DMS"
        )
        assert att2.url.startswith("http://")

    def test_pre_generated_attachment_invalid_url(self):
        """Test PreGeneratedAttachment with invalid URL."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="URL must start with http:// or https://"):
            PreGeneratedAttachment(
                url="ftp://invalid.com/file.pdf",
                source="DMS"
            )

    def test_pre_generated_attachment_invalid_source(self):
        """Test PreGeneratedAttachment with invalid source."""
        from typing import cast, Any
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match=r"Input should be 'DMS'"):
            PreGeneratedAttachment(
                url="https://example.com/file.pdf",
                source=cast(Any, "S3")
            )

    def test_pre_generated_attachment_equality(self):
        """Test PreGeneratedAttachment equality."""
        att1 = PreGeneratedAttachment(
            url="https://dms.example.com/path/file.pdf",
            source="DMS"
        )
        att2 = PreGeneratedAttachment(
            url="https://dms.example.com/path/file.pdf",
            source="DMS"
        )
        att3 = PreGeneratedAttachment(
            url="https://dms.example.com/other/file.pdf",
            source="DMS"
        )

        assert att1 == att2
        assert att1 != att3
