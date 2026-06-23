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
        """Test that unified client can be imported."""
        from sap_cloud_sdk.outputmanagement import OutputManagementClient
        assert OutputManagementClient is not None

    def test_service_client_import(self):
        """Test that service client can be imported."""
        from sap_cloud_sdk.outputmanagement._service_client import OutputManagementServiceClient
        assert OutputManagementServiceClient is not None

    def test_create_client_import(self):
        """Test that create_client factory function can be imported."""
        from sap_cloud_sdk.outputmanagement import create_client
        assert create_client is not None

    def test_constants_import(self):
        """Test that constants can be imported."""
        from sap_cloud_sdk.outputmanagement import FileFormat, Channel
        from sap_cloud_sdk.outputmanagement.constants import Constants
        
        assert Constants.API_OUTPUT_CONTROL is not None
        assert FileFormat.PDF is not None
        assert Channel.INTERNAL_EMAIL is not None

    def test_exceptions_import(self):
        """Test that exceptions can be imported."""
        from sap_cloud_sdk.outputmanagement import (
            OutputManagementException,
            ValidationException,
            AuthenticationException,
            NetworkException,
            DestinationNotFoundException,
            DestinationAccessException,
        )
        assert OutputManagementException is not None
        assert ValidationException is not None
        assert AuthenticationException is not None
        assert NetworkException is not None
        assert DestinationNotFoundException is not None
        assert DestinationAccessException is not None

    def test_models_import(self):
        """Test that models can be imported."""
        from sap_cloud_sdk.outputmanagement import (
            OutputRequest,
            OutputRequestBuilder,
            OutputResponse,
            EmailConfiguration,
            AttachmentConfig,
            PreGeneratedAttachment,
            OutputManagementInfo,
            OutputRequestData,
            DirectShareConfiguration,
            FormConfiguration,
        )
        assert OutputRequest is not None
        assert OutputRequestBuilder is not None
        assert OutputResponse is not None
        assert EmailConfiguration is not None
        assert AttachmentConfig is not None
        assert PreGeneratedAttachment is not None
        assert OutputManagementInfo is not None
        assert OutputRequestData is not None
        assert DirectShareConfiguration is not None
        assert FormConfiguration is not None

    def test_config_import(self):
        """Test that config can be imported."""
        from sap_cloud_sdk.outputmanagement import DestinationCredentialConfig
        assert DestinationCredentialConfig is not None

    def test_utils_import(self):
        """Test that utils can be imported."""
        from sap_cloud_sdk.outputmanagement.utils import RequestValidator
        assert RequestValidator is not None