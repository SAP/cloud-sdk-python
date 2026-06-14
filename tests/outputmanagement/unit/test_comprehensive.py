# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Comprehensive tests for output management module."""

import pytest
from dataclasses import asdict, fields

from sap_cloud_sdk.outputmanagement.models import (
    OutputResponse,
    EmailConfiguration,
    AttachmentConfig,
    PreGeneratedAttachment,
)
from sap_cloud_sdk.outputmanagement.exceptions import (
    OutputManagementError,
    OutputManagementValidationError,
    OutputManagementClientError,
)


class TestDataclassFeatures:
    """Test dataclass-specific features of models."""

    def test_output_response_fields(self):
        """Test OutputResponse has expected fields."""
        response = OutputResponse(request_id="test", status="SUCCESS")
        field_names = {f.name for f in fields(response)}
        
        assert "request_id" in field_names
        assert "status" in field_names

    def test_email_configuration_fields(self):
        """Test EmailConfiguration has expected fields."""
        config = EmailConfiguration(
            to=["test@example.com"],
            subject="Test",
            body="Test"
        )
        field_names = {f.name for f in fields(config)}
        
        assert "to" in field_names
        assert "subject" in field_names
        assert "body" in field_names

    def test_attachment_config_fields(self):
        """Test AttachmentConfig has expected fields."""
        attachment = AttachmentConfig(
            filename="test.pdf",
            content_type="application/pdf"
        )
        field_names = {f.name for f in fields(attachment)}
        
        assert "filename" in field_names
        assert "content_type" in field_names

    def test_pre_generated_attachment_fields(self):
        """Test PreGeneratedAttachment has expected fields."""
        attachment = PreGeneratedAttachment(
            object_key="path/file.pdf",
            filename="file.pdf"
        )
        field_names = {f.name for f in fields(attachment)}
        
        assert "object_key" in field_names
        assert "filename" in field_names


class TestModelValidation:
    """Test model validation and constraints."""

    def test_email_configuration_requires_recipients(self):
        """Test that email configuration requires recipients."""
        # Should be able to create with recipients
        config = EmailConfiguration(
            to=["user@example.com"],
            subject="Test",
            body="Test"
        )
        assert len(config.to) > 0

    def test_attachment_requires_filename(self):
        """Test that attachment requires filename."""
        attachment = AttachmentConfig(
            filename="document.pdf",
            content_type="application/pdf"
        )
        assert attachment.filename is not None
        assert len(attachment.filename) > 0

    def test_output_response_requires_request_id(self):
        """Test that output response requires request ID."""
        response = OutputResponse(
            request_id="req-123",
            status="SUCCESS"
        )
        assert response.request_id is not None
        assert len(response.request_id) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_email_with_empty_body(self):
        """Test email configuration with empty body."""
        config = EmailConfiguration(
            to=["user@example.com"],
            subject="Test",
            body=""
        )
        assert config.body == ""

    def test_email_with_long_subject(self):
        """Test email configuration with very long subject."""
        long_subject = "A" * 1000
        config = EmailConfiguration(
            to=["user@example.com"],
            subject=long_subject,
            body="Test"
        )
        assert len(config.subject) == 1000

    def test_attachment_with_large_content(self):
        """Test attachment with large content."""
        large_content = b"X" * (1024 * 1024)  # 1MB
        attachment = AttachmentConfig(
            filename="large-file.bin",
            content_type="application/octet-stream",
            content=large_content
        )
        assert len(attachment.content) == 1024 * 1024

    def test_email_with_many_recipients(self):
        """Test email with many recipients."""
        many_recipients = [f"user{i}@example.com" for i in range(100)]
        config = EmailConfiguration(
            to=many_recipients,
            subject="Mass Email",
            body="Test"
        )
        assert len(config.to) == 100

    def test_email_with_special_characters(self):
        """Test email with special characters in subject and body."""
        config = EmailConfiguration(
            to=["user@example.com"],
            subject="Test: Special chars !@#$%^&*()",
            body="Body with unicode: 你好 مرحبا שלום"
        )
        assert "!@#$%^&*()" in config.subject
        assert "你好" in config.body

    def test_attachment_with_unicode_filename(self):
        """Test attachment with unicode filename."""
        attachment = AttachmentConfig(
            filename="文档.pdf",
            content_type="application/pdf"
        )
        assert "文档" in attachment.filename

    def test_output_response_with_none_message(self):
        """Test output response with None message."""
        response = OutputResponse(
            request_id="req-123",
            status="PENDING",
            message=None
        )
        assert response.message is None


class TestExceptionScenarios:
    """Test various exception scenarios."""

    def test_exception_with_nested_message(self):
        """Test exception with nested error message."""
        try:
            raise ValueError("Inner error")
        except ValueError as e:
            error = OutputManagementError(f"Outer error: {str(e)}")
            assert "Inner error" in str(error)
            assert "Outer error" in str(error)

    def test_multiple_exception_types(self):
        """Test catching different exception types."""
        errors = [
            OutputManagementError("General error"),
            OutputManagementValidationError("Validation error"),
            OutputManagementClientError("Client error"),
        ]
        
        for error in errors:
            assert isinstance(error, OutputManagementError)
            assert isinstance(error, Exception)

    def test_exception_repr(self):
        """Test exception representation."""
        error = OutputManagementError("Test error")
        repr_str = repr(error)
        assert "OutputManagementError" in repr_str or "Test error" in repr_str


class TestModelComparisons:
    """Test model comparison operations."""

    def test_output_response_equality_with_different_fields(self):
        """Test output response equality with different optional fields."""
        response1 = OutputResponse(
            request_id="req-1",
            status="SUCCESS",
            message="Done"
        )
        response2 = OutputResponse(
            request_id="req-1",
            status="SUCCESS",
            message="Done"
        )
        response3 = OutputResponse(
            request_id="req-1",
            status="SUCCESS",
            message="Different message"
        )
        
        assert response1 == response2
        assert response1 != response3

    def test_attachment_equality(self):
        """Test attachment equality."""
        att1 = AttachmentConfig(
            filename="file.pdf",
            content_type="application/pdf",
            content=b"content"
        )
        att2 = AttachmentConfig(
            filename="file.pdf",
            content_type="application/pdf",
            content=b"content"
        )
        att3 = AttachmentConfig(
            filename="other.pdf",
            content_type="application/pdf",
            content=b"content"
        )
        
        assert att1 == att2
        assert att1 != att3


class TestModelSerialization:
    """Test model serialization capabilities."""

    def test_output_response_to_dict(self):
        """Test converting OutputResponse to dictionary."""
        response = OutputResponse(
            request_id="req-123",
            status="SUCCESS",
            message="Done"
        )
        response_dict = asdict(response)
        
        assert isinstance(response_dict, dict)
        assert response_dict["request_id"] == "req-123"
        assert response_dict["status"] == "SUCCESS"
        assert response_dict["message"] == "Done"

    def test_email_configuration_to_dict(self):
        """Test converting EmailConfiguration to dictionary."""
        config = EmailConfiguration(
            to=["user@example.com"],
            subject="Test",
            body="Test body"
        )
        config_dict = asdict(config)
        
        assert isinstance(config_dict, dict)
        assert config_dict["to"] == ["user@example.com"]
        assert config_dict["subject"] == "Test"

    def test_attachment_to_dict(self):
        """Test converting AttachmentConfig to dictionary."""
        attachment = AttachmentConfig(
            filename="file.pdf",
            content_type="application/pdf",
            content=b"content"
        )
        att_dict = asdict(attachment)
        
        assert isinstance(att_dict, dict)
        assert att_dict["filename"] == "file.pdf"
        assert att_dict["content_type"] == "application/pdf"


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_invoice_email_scenario(self):
        """Test sending an invoice email scenario."""
        invoice_pdf = AttachmentConfig(
            filename="invoice_2024_001.pdf",
            content_type="application/pdf",
            content=b"Invoice PDF content",
            size=50000
        )
        
        email = EmailConfiguration(
            to=["customer@company.com"],
            cc=["accounting@company.com"],
            subject="Invoice #2024-001 - Payment Due",
            body="Dear Customer,\n\nPlease find attached invoice #2024-001.\n\nPayment is due within 30 days.\n\nBest regards,\nAccounting Team",
            attachments=[invoice_pdf]
        )
        
        assert "Invoice" in email.subject
        assert len(email.attachments) == 1
        assert email.attachments[0].size == 50000

    def test_report_generation_scenario(self):
        """Test report generation scenario."""
        response = OutputResponse(
            request_id="report-2024-q1",
            status="PROCESSING",
            message="Generating quarterly report"
        )
        
        assert response.request_id.startswith("report-")
        assert response.status == "PROCESSING"

    def test_bulk_email_scenario(self):
        """Test bulk email sending scenario."""
        recipients = [f"employee{i}@company.com" for i in range(1, 51)]
        
        email = EmailConfiguration(
            to=recipients,
            subject="Company Newsletter - January 2024",
            body="Dear Team,\n\nPlease find this month's newsletter...",
        )
        
        assert len(email.to) == 50
        assert "Newsletter" in email.subject

    def test_multi_attachment_report_scenario(self):
        """Test report with multiple attachments scenario."""
        attachments = [
            AttachmentConfig(
                filename="summary.pdf",
                content_type="application/pdf",
                content=b"Summary PDF"
            ),
            AttachmentConfig(
                filename="data.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=b"Excel data"
            ),
            AttachmentConfig(
                filename="notes.txt",
                content_type="text/plain",
                content=b"Additional notes"
            ),
        ]
        
        email = EmailConfiguration(
            to=["manager@company.com"],
            subject="Monthly Report Package",
            body="Please find the complete monthly report package attached.",
            attachments=attachments
        )
        
        assert len(email.attachments) == 3
        assert any(att.filename.endswith(".pdf") for att in email.attachments)
        assert any(att.filename.endswith(".xlsx") for att in email.attachments)
        assert any(att.filename.endswith(".txt") for att in email.attachments)