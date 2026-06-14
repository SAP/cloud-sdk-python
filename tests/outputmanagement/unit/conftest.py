# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Pytest configuration for output management unit tests."""

import pytest


@pytest.fixture
def sample_email_config():
    """Provide a sample email configuration for testing."""
    from sap_cloud_sdk.outputmanagement.models import EmailConfiguration
    
    return EmailConfiguration(
        to=["recipient@example.com"],
        subject="Test Email",
        body="This is a test email body"
    )


@pytest.fixture
def sample_attachment():
    """Provide a sample attachment for testing."""
    from sap_cloud_sdk.outputmanagement.models import AttachmentConfig
    
    return AttachmentConfig(
        filename="test-document.pdf",
        content_type="application/pdf",
        content=b"Sample PDF content"
    )


@pytest.fixture
def sample_output_response():
    """Provide a sample output response for testing."""
    from sap_cloud_sdk.outputmanagement.models import OutputResponse
    
    return OutputResponse(
        request_id="test-req-123",
        status="SUCCESS",
        message="Test output generated successfully"
    )


@pytest.fixture
def sample_pre_generated_attachment():
    """Provide a sample pre-generated attachment for testing."""
    from sap_cloud_sdk.outputmanagement.models import PreGeneratedAttachment
    
    return PreGeneratedAttachment(
        object_key="attachments/test-file.pdf",
        filename="test-file.pdf",
        content_type="application/pdf",
        size=1024
    )


@pytest.fixture
def sample_destination_config():
    """Provide a sample destination configuration for testing."""
    from sap_cloud_sdk.outputmanagement.config.destination_credential_config import (
        DestinationCredentialConfig,
    )
    
    return DestinationCredentialConfig(
        destination_name="test-output-management"
    )