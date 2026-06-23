# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Pytest configuration for output management unit tests."""

import pytest


@pytest.fixture
def sample_email_config():
    """Provide a sample email configuration for testing."""
    from sap_cloud_sdk.outputmanagement import EmailConfiguration

    return EmailConfiguration(
        emailNotificationTemplateKey="TEST_TEMPLATE",
        emailTemplateLanguage="en",
        to=["recipient@example.com"]
    )


@pytest.fixture
def sample_attachment():
    """Provide a sample attachment for testing."""
    from sap_cloud_sdk.outputmanagement import AttachmentConfig, FormConfiguration

    form_config = FormConfiguration(form_id="test-form")
    return AttachmentConfig(formConfiguration=form_config)


@pytest.fixture
def sample_output_response():
    """Provide a sample output response for testing."""
    from sap_cloud_sdk.outputmanagement import OutputResponse

    return OutputResponse(outputRequestId="test-req-123")


@pytest.fixture
def sample_pre_generated_attachment():
    """Provide a sample pre-generated attachment for testing."""
    from sap_cloud_sdk.outputmanagement import PreGeneratedAttachment

    return PreGeneratedAttachment(
        url="https://dms.example.com/attachments/test-file.pdf",
        source="DMS"
    )


@pytest.fixture
def sample_destination_config():
    """Provide a sample destination configuration for testing."""
    from sap_cloud_sdk.outputmanagement import DestinationCredentialConfig

    return DestinationCredentialConfig(
        destination_name="test-output-management"
    )
