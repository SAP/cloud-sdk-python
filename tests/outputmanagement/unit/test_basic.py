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
        from sap_cloud_sdk.outputmanagement.client import OutputManagementServiceClient
        assert OutputManagementServiceClient is not None

    def test_client_provider_import(self):
        """Test that client provider can be imported."""
        from sap_cloud_sdk.outputmanagement.client_provider import OutputManagementServiceClientProvider
        assert OutputManagementServiceClientProvider is not None

    def test_constants_import(self):
        """Test that constants can be imported."""
        from sap_cloud_sdk.outputmanagement.constants import (
            Constants,
            FileFormat,
            Channel,
        )
        assert Constants.API_OUTPUT_CONTROL is not None
        assert FileFormat.PDF is not None
        assert Channel.EMAIL is not None

    def test_exceptions_import(self):
        """Test that exceptions can be imported."""
        from sap_cloud_sdk.outputmanagement.exceptions import (
            OutputManagementException,
            ValidationException,
            AuthenticationException,
            NetworkException,
        )
        assert OutputManagementException is not None
        assert ValidationException is not None
        assert AuthenticationException is not None
        assert NetworkException is not None

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
