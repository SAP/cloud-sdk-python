# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Basic unit tests for output management module."""

import pytest


class TestOutputManagementModule:
    """Test basic output management module functionality."""

    def test_module_imports(self):
        """Test that output management module can be imported."""
        from sap_cloud_sdk import outputmanagement
        assert outputmanagement is not None

    def test_client_import(self):
        """Test that client can be imported."""
        from sap_cloud_sdk.outputmanagement.client import OutputManagementClient
        assert OutputManagementClient is not None

    def test_client_provider_import(self):
        """Test that client provider can be imported."""
        from sap_cloud_sdk.outputmanagement.client_provider import OutputManagementClientProvider
        assert OutputManagementClientProvider is not None

    def test_constants_import(self):
        """Test that constants can be imported."""
        from sap_cloud_sdk.outputmanagement.constants import (
            DEFAULT_DESTINATION_NAME,
            OUTPUT_MANAGEMENT_SERVICE_PATH,
            EMAIL_SERVICE_PATH,
        )
        assert DEFAULT_DESTINATION_NAME is not None
        assert OUTPUT_MANAGEMENT_SERVICE_PATH is not None
        assert EMAIL_SERVICE_PATH is not None

    def test_exceptions_import(self):
        """Test that exceptions can be imported."""
        from sap_cloud_sdk.outputmanagement.exceptions import (
            OutputManagementError,
            OutputManagementValidationError,
            OutputManagementClientError,
        )
        assert OutputManagementError is not None
        assert OutputManagementValidationError is not None
        assert OutputManagementClientError is not None

    def test_models_import(self):
        """Test that models can be imported."""
        from sap_cloud_sdk.outputmanagement.models import (
            OutputResponse,
            EmailConfiguration,
            AttachmentConfig,
            PreGeneratedAttachment,
        )
        assert OutputResponse is not None
        assert EmailConfiguration is not None
        assert AttachmentConfig is not None
        assert PreGeneratedAttachment is not None

    def test_clients_import(self):
        """Test that clients can be imported."""
        from sap_cloud_sdk.outputmanagement.clients.output_requests_client import (
            OutputRequestsClient,
        )
        from sap_cloud_sdk.outputmanagement.clients.email_client import EmailClient
        
        assert OutputRequestsClient is not None
        assert EmailClient is not None

    def test_config_import(self):
        """Test that config can be imported."""
        from sap_cloud_sdk.outputmanagement.config.destination_credential_config import (
            DestinationCredentialConfig,
        )
        assert DestinationCredentialConfig is not None

    def test_utils_import(self):
        """Test that utils can be imported."""
        from sap_cloud_sdk.outputmanagement.utils.request_validator import (
            RequestValidator,
        )
        assert RequestValidator is not None