# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for output management models."""

import pytest
from dataclasses import is_dataclass

from sap_cloud_sdk.outputmanagement.models import (
    OutputResponse,
    EmailConfiguration,
    AttachmentConfig,
    PreGeneratedAttachment,
)


class TestOutputResponse:
    """Test OutputResponse model."""

    def test_output_response_is_dataclass(self):
        """Test that OutputResponse is a dataclass."""
        assert is_dataclass(OutputResponse)

    def test_output_response_creation_basic(self):
        """Test creating a basic OutputResponse."""
        response = OutputResponse(
            request_id="req-123",
            status="SUCCESS"
        )
        assert response.request_id == "req-123"
        assert response.status == "SUCCESS"

    def test_output_response_with_all_fields(self):
        """Test OutputResponse with all fields."""
        response = OutputResponse(
            request_id="req-456",
            status="PENDING",
            message="Processing",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:01:00Z"
        )
        assert response.request_id == "req-456"
        assert response.status == "PENDING"
        assert response.message == "Processing"
        assert response.created_at == "2024-01-01T00:00:00Z"
        assert response.updated_at == "2024-01-01T00:01:00Z"

    def test_output_response_equality(self):
        """Test OutputResponse equality."""
        response1 = OutputResponse(request_id="req-1", status="SUCCESS")
        response2 = OutputResponse(request_id="req-1", status="SUCCESS")
        response3 = OutputResponse(request_id="req-2", status="SUCCESS")
        
        assert response1 == response2
        assert response1 != response3


class TestEmailConfiguration:
    """Test EmailConfiguration model."""

    def test_email_configuration_is_dataclass(self):
        """Test that EmailConfiguration is a dataclass."""
        assert is_dataclass(EmailConfiguration)

    def test_email_configuration_basic(self):
        """Test basic EmailConfiguration creation."""
        config = EmailConfiguration(
            to=["recipient@example.com"],
            subject="Test Email",
            body="This is a test email"
        )
        assert config.to == ["recipient@example.com"]
        assert config.subject == "Test Email"
        assert config.body == "This is a test email"

    def test_email_configuration_with_cc_bcc(self):
        """Test EmailConfiguration with CC and BCC."""
        config = EmailConfiguration(
            to=["recipient@example.com"],
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
            subject="Test Email",
            body="Test body"
        )
        assert config.cc == ["cc@example.com"]
        assert config.bcc == ["bcc@example.com"]

    def test_email_configuration_multiple_recipients(self):
        """Test EmailConfiguration with multiple recipients."""
        config = EmailConfiguration(
            to=["user1@example.com", "user2@example.com", "user3@example.com"],
            subject="Multi-recipient Email",
            body="Test"
        )
        assert len(config.to) == 3
        assert "user1@example.com" in config.to
        assert "user2@example.com" in config.to
        assert "user3@example.com" in config.to

    def test_email_configuration_with_attachments(self):
        """Test EmailConfiguration with attachments."""
        attachment = AttachmentConfig(
            filename="document.pdf",
            content_type="application/pdf",
            content=b"PDF content"
        )
        config = EmailConfiguration(
            to=["recipient@example.com"],
            subject="Email with Attachment",
            body="Please find attached",
            attachments=[attachment]
        )
        assert len(config.attachments) == 1
        assert config.attachments[0].filename == "document.pdf"

    def test_email_configuration_empty_lists_default(self):
        """Test EmailConfiguration with default empty lists."""
        config = EmailConfiguration(
            to=["recipient@example.com"],
            subject="Test",
            body="Test"
        )
        # Check that optional list fields have appropriate defaults
        assert hasattr(config, 'cc')
        assert hasattr(config, 'bcc')
        assert hasattr(config, 'attachments')


class TestAttachmentConfig:
    """Test AttachmentConfig model."""

    def test_attachment_config_is_dataclass(self):
        """Test that AttachmentConfig is a dataclass."""
        assert is_dataclass(AttachmentConfig)

    def test_attachment_config_basic(self):
        """Test basic AttachmentConfig creation."""
        attachment = AttachmentConfig(
            filename="report.pdf",
            content_type="application/pdf"
        )
        assert attachment.filename == "report.pdf"
        assert attachment.content_type == "application/pdf"

    def test_attachment_config_with_content(self):
        """Test AttachmentConfig with content."""
        content = b"Sample PDF content"
        attachment = AttachmentConfig(
            filename="data.pdf",
            content_type="application/pdf",
            content=content
        )
        assert attachment.content == content
        assert isinstance(attachment.content, bytes)

    def test_attachment_config_various_types(self):
        """Test AttachmentConfig with various content types."""
        pdf = AttachmentConfig(filename="doc.pdf", content_type="application/pdf")
        csv = AttachmentConfig(filename="data.csv", content_type="text/csv")
        xml = AttachmentConfig(filename="config.xml", content_type="application/xml")
        txt = AttachmentConfig(filename="readme.txt", content_type="text/plain")
        
        assert pdf.content_type == "application/pdf"
        assert csv.content_type == "text/csv"
        assert xml.content_type == "application/xml"
        assert txt.content_type == "text/plain"

    def test_attachment_config_with_size(self):
        """Test AttachmentConfig with size information."""
        attachment = AttachmentConfig(
            filename="large-file.pdf",
            content_type="application/pdf",
            content=b"x" * 1024,
            size=1024
        )
        assert attachment.size == 1024
        assert len(attachment.content) == 1024


class TestPreGeneratedAttachment:
    """Test PreGeneratedAttachment model."""

    def test_pre_generated_attachment_is_dataclass(self):
        """Test that PreGeneratedAttachment is a dataclass."""
        assert is_dataclass(PreGeneratedAttachment)

    def test_pre_generated_attachment_basic(self):
        """Test basic PreGeneratedAttachment creation."""
        attachment = PreGeneratedAttachment(
            object_key="attachments/report-123.pdf",
            filename="report.pdf"
        )
        assert attachment.object_key == "attachments/report-123.pdf"
        assert attachment.filename == "report.pdf"

    def test_pre_generated_attachment_with_metadata(self):
        """Test PreGeneratedAttachment with metadata."""
        attachment = PreGeneratedAttachment(
            object_key="docs/invoice-456.pdf",
            filename="invoice.pdf",
            content_type="application/pdf",
            size=102400
        )
        assert attachment.content_type == "application/pdf"
        assert attachment.size == 102400

    def test_pre_generated_attachment_object_key_formats(self):
        """Test PreGeneratedAttachment with various object key formats."""
        att1 = PreGeneratedAttachment(
            object_key="folder/subfolder/file.pdf",
            filename="file.pdf"
        )
        att2 = PreGeneratedAttachment(
            object_key="simple-file.txt",
            filename="simple-file.txt"
        )
        att3 = PreGeneratedAttachment(
            object_key="deep/nested/path/to/document.docx",
            filename="document.docx"
        )
        
        assert "/" in att1.object_key
        assert "/" not in att2.object_key
        assert att3.object_key.count("/") == 3

    def test_pre_generated_attachment_equality(self):
        """Test PreGeneratedAttachment equality."""
        att1 = PreGeneratedAttachment(
            object_key="path/file.pdf",
            filename="file.pdf"
        )
        att2 = PreGeneratedAttachment(
            object_key="path/file.pdf",
            filename="file.pdf"
        )
        att3 = PreGeneratedAttachment(
            object_key="other/file.pdf",
            filename="file.pdf"
        )
        
        assert att1 == att2
        assert att1 != att3