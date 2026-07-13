# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the output management client."""

from unittest.mock import Mock, patch

import pytest

from sap_cloud_sdk.outputmanagement import OutputManagementClient
from sap_cloud_sdk.outputmanagement._service_client import OutputManagementServiceClient
from sap_cloud_sdk.outputmanagement._models import OutputRequest, OutputResponse
from sap_cloud_sdk.core.telemetry import Module, Operation


class TestOutputManagementClient:
    """Test suite for OutputManagementClient."""

    def test_send_email_calls_service_client(self):
        """Test that send_email delegates to service client."""
        mock_service_client = Mock(spec=OutputManagementServiceClient)
        mock_service_client.send_output_request.return_value = OutputResponse(
            outputRequestId="req-123"
        )

        client = OutputManagementClient(service_client=mock_service_client)

        response = client.send_email(
            notification_template_key="TEST_TEMPLATE",
            to=["user@example.com"],
            business_document={"Document": {"id": "123"}},
        )

        assert response.output_request_id == "req-123"
        mock_service_client.send_output_request.assert_called_once()

    def test_send_output_request_calls_service_client(self):
        """Test that send_output_request delegates to service client."""
        mock_service_client = Mock(spec=OutputManagementServiceClient)
        mock_service_client.send_output_request.return_value = OutputResponse(
            outputRequestId="req-456"
        )

        client = OutputManagementClient(service_client=mock_service_client)
        output_request = Mock(spec=OutputRequest)

        response = client.send_output_request(output_request)

        assert response.output_request_id == "req-456"
        mock_service_client.send_output_request.assert_called_once_with(output_request)

    def test_send_email_records_request_metric(self):
        """Test that send_email records request metric."""
        mock_service_client = Mock(spec=OutputManagementServiceClient)
        mock_service_client.send_output_request.return_value = OutputResponse(
            outputRequestId="req-123"
        )

        client = OutputManagementClient(service_client=mock_service_client)

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
        ) as mock_metric:
            response = client.send_email(
                notification_template_key="TEST_TEMPLATE",
                to=["user@example.com"],
                business_document={"Document": {"id": "123"}},
            )

            mock_metric.assert_called_once_with(
                Module.OUTPUT_MANAGEMENT,
                None,
                Operation.OUTPUT_MANAGEMENT_SEND_EMAIL,
                False,
            )

            assert response.output_request_id == "req-123"

    def test_send_output_request_records_request_metric(self):
        """Test that send_output_request records request metric."""
        mock_service_client = Mock(spec=OutputManagementServiceClient)
        mock_service_client.send_output_request.return_value = OutputResponse(
            outputRequestId="req-456"
        )

        client = OutputManagementClient(service_client=mock_service_client)
        output_request = Mock(spec=OutputRequest)

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
        ) as mock_metric:
            response = client.send_output_request(output_request)

            mock_metric.assert_called_once_with(
                Module.OUTPUT_MANAGEMENT,
                None,
                Operation.OUTPUT_MANAGEMENT_SEND_OUTPUT_REQUEST,
                False,
            )

            assert response.output_request_id == "req-456"

    @pytest.mark.asyncio
    async def test_send_email_with_mcp_records_request_metric(self):
        """Test that send_email_with_mcp records request metric."""
        mock_service_client = Mock(spec=OutputManagementServiceClient)
        client = OutputManagementClient(service_client=mock_service_client)

        # Mock MCP tool
        mock_mcp_tool = Mock()
        mock_mcp_tool.ainvoke = Mock(return_value="mcp_result")

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
        ) as mock_metric:
            result = await client.send_email_with_mcp(
                tool_name="sendEmail",
                notification_template_key="TEST_TEMPLATE",
                to_emails=["user@example.com"],
                business_document={"Document": {"id": "123"}},
                mcp_tool=mock_mcp_tool,
            )

            mock_metric.assert_called_once_with(
                Module.OUTPUT_MANAGEMENT,
                None,
                Operation.OUTPUT_MANAGEMENT_SEND_EMAIL_WITH_MCP,
                False,
            )

            assert result == "mcp_result"

    def test_send_email_with_validation_error_does_not_call_service(self):
        """Test that validation errors prevent service client calls."""
        mock_service_client = Mock(spec=OutputManagementServiceClient)
        client = OutputManagementClient(service_client=mock_service_client)

        response = client.send_email(
            notification_template_key="",  # Invalid: empty template key
            to=[],  # Invalid: no recipients
            business_document={},  # Invalid: empty document
        )

        # Should return error response without calling service client
        assert response.error is not None
        mock_service_client.send_output_request.assert_not_called()

    def test_create_output_request_returns_valid_request(self):
        """Test that create_output_request creates a valid OutputRequest."""
        mock_service_client = Mock(spec=OutputManagementServiceClient)
        client = OutputManagementClient(service_client=mock_service_client)

        output_request = client.create_output_request(
            notification_template_key="TEST_TEMPLATE",
            to=["user@example.com"],
            business_document={"Document": {"id": "123"}},
        )

        assert output_request is not None
        assert isinstance(output_request, OutputRequest)
        assert output_request.data is not None
        assert output_request.data.OutputManagement is not None
