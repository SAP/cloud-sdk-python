# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Integration-style unit tests for output management module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from sap_cloud_sdk.outputmanagement.client import OutputManagementServiceClient
from sap_cloud_sdk.outputmanagement.client_provider import OutputManagementServiceClientProvider
from sap_cloud_sdk.outputmanagement.config.destination_credential_config import (
    DestinationCredentialConfig,
)
from sap_cloud_sdk.outputmanagement.models import (
    EmailConfiguration,
    AttachmentConfig,
    OutputResponse,
)
from sap_cloud_sdk.outputmanagement.exceptions import (
    OutputManagementException,
    ValidationException,
)


class TestOutputManagementIntegration:
    """Integration-style tests for output management."""

    def test_end_to_end_email_workflow(self):
        """Test complete email sending workflow."""
        # Create email configuration
        attachment = AttachmentConfig(
            filename="report.pdf",
            content_type="application/pdf",
            content=b"PDF content"
        )
        
        email_config = EmailConfiguration(
            to=["recipient@example.com"],
            cc=["cc@example.com"],
            subject="Monthly Report",
            body="Please find the monthly report attached.",
            attachments=[attachment]
        )
        
        # Verify configuration is created correctly
        assert email_config.to == ["recipient@example.com"]
        assert email_config.cc == ["cc@example.com"]
        assert email_config.subject == "Monthly Report"
        assert len(email_config.attachments) == 1
        assert email_config.attachments[0].filename == "report.pdf"

    def test_end_to_end_output_request_workflow(self):
        """Test complete output request workflow."""
        # Create output response
        response = OutputResponse(
            request_id="req-12345",
            status="SUCCESS",
            message="Output generated successfully"
        )
        
        # Verify response
        assert response.request_id == "req-12345"
        assert response.status == "SUCCESS"
        assert response.message == "Output generated successfully"

    def test_configuration_creation_workflow(self):
        """Test configuration creation workflow."""
        # Test with destination name
        config1 = DestinationCredentialConfig(
            destination_name="output-management-dest"
        )
        assert config1.destination_name == "output-management-dest"
        
        # Test with URL and credentials
        config2 = DestinationCredentialConfig(
            url="https://api.example.com",
            username="testuser",
            password="testpass"
        )
        assert config2.url == "https://api.example.com"
        assert config2.username == "testuser"
        assert config2.password == "testpass"

    def test_multiple_attachments_workflow(self):
        """Test workflow with multiple attachments."""
        attachments = [
            AttachmentConfig(
                filename="report1.pdf",
                content_type="application/pdf",
                content=b"PDF 1"
            ),
            AttachmentConfig(
                filename="data.csv",
                content_type="text/csv",
                content=b"CSV data"
            ),
            AttachmentConfig(
                filename="summary.txt",
                content_type="text/plain",
                content=b"Summary text"
            ),
        ]
        
        email_config = EmailConfiguration(
            to=["recipient@example.com"],
            subject="Multiple Attachments",
            body="Please find multiple files attached.",
            attachments=attachments
        )
        
        assert len(email_config.attachments) == 3
        assert email_config.attachments[0].content_type == "application/pdf"
        assert email_config.attachments[1].content_type == "text/csv"
        assert email_config.attachments[2].content_type == "text/plain"

    def test_multiple_recipients_workflow(self):
        """Test workflow with multiple recipients."""
        email_config = EmailConfiguration(
            to=[
                "user1@example.com",
                "user2@example.com",
                "user3@example.com"
            ],
            cc=["manager@example.com"],
            bcc=["archive@example.com"],
            subject="Team Update",
            body="Important team update"
        )
        
        assert len(email_config.to) == 3
        assert len(email_config.cc) == 1
        assert len(email_config.bcc) == 1

    def test_error_handling_workflow(self):
        """Test error handling in workflow."""
        # Test that exceptions can be raised and caught
        with pytest.raises(OutputManagementException):
            raise OutputManagementException("General error")
        
        with pytest.raises(ValidationException):
            raise ValidationException("Validation error")

    def test_dataclass_immutability_workflow(self):
        """Test that dataclass instances work as expected."""
        response1 = OutputResponse(request_id="req-1", status="SUCCESS")
        response2 = OutputResponse(request_id="req-1", status="SUCCESS")
        response3 = OutputResponse(request_id="req-2", status="SUCCESS")
        
        # Test equality
        assert response1 == response2
        assert response1 != response3
        
        # Test that we can access fields
        assert response1.request_id == "req-1"
        assert response1.status == "SUCCESS"

    def test_complex_email_scenario(self):
        """Test complex email scenario with all features."""
        # Create multiple attachments
        pdf_attachment = AttachmentConfig(
            filename="invoice.pdf",
            content_type="application/pdf",
            content=b"Invoice PDF content",
            size=1024
        )
        
        csv_attachment = AttachmentConfig(
            filename="details.csv",
            content_type="text/csv",
            content=b"Detail,Value\nItem1,100\nItem2,200",
            size=512
        )
        
        # Create email with all features
        email_config = EmailConfiguration(
            to=["customer@example.com", "billing@example.com"],
            cc=["manager@example.com"],
            bcc=["archive@example.com", "audit@example.com"],
            subject="Invoice #12345 - Payment Due",
            body="Dear Customer,\n\nPlease find your invoice attached.\n\nBest regards,\nBilling Team",
            attachments=[pdf_attachment, csv_attachment]
        )
        
        # Verify all components
        assert len(email_config.to) == 2
        assert len(email_config.cc) == 1
        assert len(email_config.bcc) == 2
        assert len(email_config.attachments) == 2
        assert "Invoice" in email_config.subject
        assert "Dear Customer" in email_config.body

    def test_output_response_lifecycle(self):
        """Test output response through different states."""
        # Pending state
        pending = OutputResponse(
            request_id="req-100",
            status="PENDING",
            message="Request submitted"
        )
        assert pending.status == "PENDING"
        
        # Processing state
        processing = OutputResponse(
            request_id="req-100",
            status="PROCESSING",
            message="Generating output"
        )
        assert processing.status == "PROCESSING"
        
        # Success state
        success = OutputResponse(
            request_id="req-100",
            status="SUCCESS",
            message="Output generated successfully"
        )
        assert success.status == "SUCCESS"
        
        # Error state
        error = OutputResponse(
            request_id="req-100",
            status="ERROR",
            message="Failed to generate output"
        )
        assert error.status == "ERROR"