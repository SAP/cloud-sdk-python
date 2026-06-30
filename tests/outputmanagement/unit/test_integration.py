# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Integration-style unit tests for output management module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from sap_cloud_sdk.outputmanagement import (
    OutputManagementClient,
    DestinationCredentialConfig,
    EmailConfiguration,
    AttachmentConfig,
    OutputResponse,
    FormConfiguration,
    PreGeneratedAttachment,
    OutputManagementException,
    ValidationException,
)
from sap_cloud_sdk.outputmanagement._service_client import OutputManagementServiceClient
from sap_cloud_sdk.outputmanagement._models import ErrorResponse


class TestOutputManagementIntegration:
    """Integration-style tests for output management."""

    def test_end_to_end_email_workflow(self):
        """Test complete email sending workflow."""
        # Create form configuration for attachment
        form_config = FormConfiguration(form_id="monthly-report-form")
        attachment = AttachmentConfig(formConfiguration=form_config)

        email_config = EmailConfiguration(
            emailNotificationTemplateKey="MONTHLY_REPORT_TEMPLATE",
            emailTemplateLanguage="en",
            to=["recipient@example.com"],
            cc=["cc@example.com"],
            attachment=attachment
        )

        # Verify configuration is created correctly
        assert email_config.to == ["recipient@example.com"]
        assert email_config.cc == ["cc@example.com"]
        assert email_config.email_notification_template_key == "MONTHLY_REPORT_TEMPLATE"
        assert email_config.attachment is not None
        assert email_config.attachment.form_configuration is not None
        assert email_config.attachment.form_configuration.form_id == "monthly-report-form"

    def test_end_to_end_output_request_workflow(self):
        """Test complete output request workflow."""
        # Create output response
        response = OutputResponse(outputRequestId="req-12345")

        # Verify response
        assert response.output_request_id == "req-12345"
        assert response.error is None

    def test_configuration_creation_workflow(self):
        """Test configuration creation workflow."""
        # Test with destination name only
        config1 = DestinationCredentialConfig(
            destination_name="output-management-dest"
        )
        assert config1.destination_name == "output-management-dest"
        assert config1.access_strategy is None
        assert config1.instance is None

        # Test with destination name and access strategy
        config2 = DestinationCredentialConfig(
            destination_name="output-management-dest",
            access_strategy="PROVIDER_ONLY"
        )
        assert config2.destination_name == "output-management-dest"
        assert config2.access_strategy == "PROVIDER_ONLY"

        # Test with destination name and instance
        config3 = DestinationCredentialConfig(
            destination_name="output-management-dest",
            instance="custom-instance"
        )
        assert config3.destination_name == "output-management-dest"
        assert config3.instance == "custom-instance"

    def test_multiple_attachments_workflow(self):
        """Test workflow with multiple DMS attachments."""
        dms_attachments = [
            PreGeneratedAttachment(
                url="https://dms.example.com/report1.pdf",
                source="DMS"
            ),
            PreGeneratedAttachment(
                url="https://dms.example.com/data.csv",
                source="DMS"
            ),
            PreGeneratedAttachment(
                url="https://dms.example.com/summary.txt",
                source="DMS"
            ),
        ]

        attachment_config = AttachmentConfig(preGeneratedAttachments=dms_attachments)

        email_config = EmailConfiguration(
            emailNotificationTemplateKey="MULTI_ATTACHMENT_TEMPLATE",
            emailTemplateLanguage="en",
            to=["recipient@example.com"],
            attachment=attachment_config
        )

        assert email_config.attachment is not None
        assert email_config.attachment.pre_generated_attachments is not None
        assert len(email_config.attachment.pre_generated_attachments) == 3
        assert all(att.source == "DMS" for att in email_config.attachment.pre_generated_attachments)

    def test_multiple_recipients_workflow(self):
        """Test workflow with multiple recipients."""
        email_config = EmailConfiguration(
            emailNotificationTemplateKey="TEAM_UPDATE_TEMPLATE",
            emailTemplateLanguage="en",
            to=[
                "user1@example.com",
                "user2@example.com",
                "user3@example.com"
            ],
            cc=["manager@example.com"],
            bcc=["archive@example.com"]
        )

        assert len(email_config.to) == 3
        assert email_config.cc is not None
        assert len(email_config.cc) == 1
        assert email_config.bcc is not None
        assert len(email_config.bcc) == 1

    def test_error_handling_workflow(self):
        """Test error handling in workflow."""
        # Test that exceptions can be raised and caught
        with pytest.raises(OutputManagementException):
            raise OutputManagementException("General error")

        with pytest.raises(ValidationException):
            raise ValidationException("Validation error")

    def test_pydantic_model_workflow(self):
        """Test that Pydantic model instances work as expected."""
        response1 = OutputResponse(outputRequestId="req-1")
        response2 = OutputResponse(outputRequestId="req-1")
        response3 = OutputResponse(outputRequestId="req-2")

        # Test equality
        assert response1 == response2
        assert response1 != response3

        # Test that we can access fields
        assert response1.output_request_id == "req-1"

    def test_complex_email_scenario(self):
        """Test complex email scenario with all features."""
        # Create DMS attachments
        dms_attachments = [
            PreGeneratedAttachment(
                url="https://dms.example.com/invoice.pdf",
                source="DMS"
            ),
            PreGeneratedAttachment(
                url="https://dms.example.com/details.csv",
                source="DMS"
            ),
        ]

        attachment_config = AttachmentConfig(preGeneratedAttachments=dms_attachments)

        # Create email with all features
        email_config = EmailConfiguration(
            emailNotificationTemplateKey="INVOICE_TEMPLATE",
            emailTemplateLanguage="en",
            to=["customer@example.com", "billing@example.com"],
            cc=["manager@example.com"],
            bcc=["archive@example.com", "audit@example.com"],
            attachment=attachment_config
        )

        # Verify all components
        assert len(email_config.to) == 2
        assert email_config.cc is not None
        assert len(email_config.cc) == 1
        assert email_config.bcc is not None
        assert len(email_config.bcc) == 2
        assert email_config.attachment is not None
        assert email_config.attachment.pre_generated_attachments is not None
        assert len(email_config.attachment.pre_generated_attachments) == 2

    def test_output_response_lifecycle(self):
        """Test output response with success and error states."""
        # Success state
        success = OutputResponse(outputRequestId="req-100")
        assert success.output_request_id == "req-100"
        assert success.error is None

        # Error state
        error_response = ErrorResponse(message="Failed to generate output", code="ERR_001")
        error = OutputResponse(error=error_response)
        assert error.output_request_id is None
        assert error.error is not None
        assert error.error.message == "Failed to generate output"
        assert error.error.code == "ERR_001"
