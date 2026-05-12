"""Tests for ExtensibilityClient and create_client."""

from unittest.mock import MagicMock, patch


from sap_cloud_sdk.extensibility import create_client
from sap_cloud_sdk.extensibility.client import ExtensibilityClient
from sap_cloud_sdk.extensibility._models import (
    ExtensionCapabilityImplementation,
    McpServer,
    Hook,
    HookType,
    DeploymentType,
    OnFailure,
    ExecutionMode,
    N8nWorkflowConfig,
)
from http import HTTPMethod
from sap_cloud_sdk.extensibility.config import ExtensibilityConfig
from sap_cloud_sdk.extensibility.exceptions import TransportError


class TestCreateClient:
    """Tests for the create_client factory."""

    @patch("sap_cloud_sdk.extensibility.UmsTransport")
    def test_uses_default_config(self, mock_transport_cls):
        client = create_client("sap.ai:agent:test:v1")
        assert isinstance(client, ExtensibilityClient)
        call_args = mock_transport_cls.call_args
        assert call_args[0][0] == "sap.ai:agent:test:v1"
        config_arg = call_args[0][1]
        assert isinstance(config_arg, ExtensibilityConfig)
        assert config_arg.destination_name is None
        assert config_arg.destination_instance == "default"

    @patch("sap_cloud_sdk.extensibility.UmsTransport")
    def test_custom_config(self, mock_transport_cls):
        config = ExtensibilityConfig(destination_name="MY_DEST")
        client = create_client("sap.ai:agent:test:v1", config=config)
        mock_transport_cls.assert_called_once_with("sap.ai:agent:test:v1", config)
        assert isinstance(client, ExtensibilityClient)

    @patch("sap_cloud_sdk.extensibility.UmsTransport")
    def test_graceful_degradation_on_transport_failure(self, mock_transport_cls):
        """create_client() returns a no-op client instead of raising."""
        mock_transport_cls.side_effect = RuntimeError("init failed")

        client = create_client("sap.ai:agent:test:v1")

        # Should return a usable client, not raise
        assert isinstance(client, ExtensibilityClient)

        # The client should return empty results
        result = client.get_extension_capability_implementation(tenant=_TENANT)
        assert isinstance(result, ExtensionCapabilityImplementation)
        assert result.mcp_servers == []
        assert result.instruction is None
        assert result.hooks == []

    @patch("sap_cloud_sdk.extensibility.UmsTransport")
    def test_graceful_degradation_logs_error(self, mock_transport_cls):
        """create_client() logs the error when falling back to no-op."""
        mock_transport_cls.side_effect = RuntimeError("init failed")

        with patch("sap_cloud_sdk.extensibility._logger") as mock_logger:
            create_client("sap.ai:agent:test:v1")
            mock_logger.error.assert_called_once()
            assert (
                "Failed to create extensibility client"
                in mock_logger.error.call_args[0][0]
            )


_TENANT = "1d2e1a41-a28b-431f-9e3f-42e9704bfa75"


class TestExtensibilityClientGetExtensionCapabilityImplementation:
    """Tests for ExtensibilityClient.get_extension_capability_implementation."""

    def test_success(self):
        expected = ExtensionCapabilityImplementation(
            capability_id="default",
            mcp_servers=[
                McpServer(
                    ord_id="sap.mcp:apiResource:serviceNow:v1",
                    global_tenant_id="tenant-sn-1",
                    tool_names=["create_ticket"],
                )
            ],
            instruction="Use with care.",
            hooks=[
                Hook(
                    hook_id="agent_pre_hook",
                    id="9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
                    n8n_workflow_config=N8nWorkflowConfig(
                        workflow_id="wf-pre-001",
                        method=HTTPMethod.POST,
                    ),
                    name="Before Agent Hook",
                    type=HookType.BEFORE,
                    deployment_type=DeploymentType.N8N,
                    timeout=30,
                    execution_mode=ExecutionMode.SYNC,
                    on_failure=OnFailure.CONTINUE,
                    order=1,
                    can_short_circuit=True,
                ),
                Hook(
                    hook_id="agent_post_hook",
                    id="6a9e0cef-eed6-4f1b-9f86-3d8e9f5c1d22",
                    n8n_workflow_config=N8nWorkflowConfig(
                        workflow_id="wf-post-001",
                        method=HTTPMethod.POST,
                    ),
                    name="After Agent Hook",
                    type=HookType.AFTER,
                    deployment_type=DeploymentType.N8N,
                    timeout=30,
                    execution_mode=ExecutionMode.SYNC,
                    on_failure=OnFailure.CONTINUE,
                    order=1,
                    can_short_circuit=True,
                ),
            ],
        )
        mock_transport = MagicMock()
        mock_transport.get_extension_capability_implementation.return_value = expected

        client = ExtensibilityClient(mock_transport)
        result = client.get_extension_capability_implementation(tenant=_TENANT)

        mock_transport.get_extension_capability_implementation.assert_called_once_with(
            capability_id="default",
            skip_cache=False,
            tenant=_TENANT,
        )
        assert result is expected

    def test_graceful_degradation_on_transport_error(self):
        mock_transport = MagicMock()
        mock_transport.get_extension_capability_implementation.side_effect = (
            TransportError("service unavailable")
        )
        client = ExtensibilityClient(mock_transport)
        result = client.get_extension_capability_implementation(tenant=_TENANT)

        assert isinstance(result, ExtensionCapabilityImplementation)
        assert result.capability_id == "default"
        assert result.mcp_servers == []
        assert result.instruction is None
        assert result.hooks == []

    def test_graceful_degradation_on_unexpected_error(self):
        mock_transport = MagicMock()
        mock_transport.get_extension_capability_implementation.side_effect = (
            RuntimeError("unexpected")
        )
        client = ExtensibilityClient(mock_transport)
        result = client.get_extension_capability_implementation(tenant=_TENANT)

        assert isinstance(result, ExtensionCapabilityImplementation)
        assert result.capability_id == "default"
        assert result.mcp_servers == []
        assert result.hooks == []

    def test_capability_id_passed_to_transport(self):
        mock_transport = MagicMock()
        mock_transport.get_extension_capability_implementation.return_value = (
            ExtensionCapabilityImplementation(capability_id="custom")
        )
        client = ExtensibilityClient(mock_transport)
        result = client.get_extension_capability_implementation(
            tenant=_TENANT, capability_id="custom"
        )

        mock_transport.get_extension_capability_implementation.assert_called_once_with(
            capability_id="custom",
            skip_cache=False,
            tenant=_TENANT,
        )
        assert result.capability_id == "custom"

    def test_fallback_uses_provided_capability_id(self):
        mock_transport = MagicMock()
        mock_transport.get_extension_capability_implementation.side_effect = (
            TransportError("service unavailable")
        )
        client = ExtensibilityClient(mock_transport)
        result = client.get_extension_capability_implementation(
            tenant=_TENANT, capability_id="my-capability"
        )

        assert result.capability_id == "my-capability"
        assert result.mcp_servers == []
        assert result.hooks == []

    def test_error_logging(self):
        mock_transport = MagicMock()
        mock_transport.get_extension_capability_implementation.side_effect = (
            TransportError("boom")
        )
        client = ExtensibilityClient(mock_transport)

        with patch("sap_cloud_sdk.extensibility.client.logger") as mock_logger:
            client.get_extension_capability_implementation(tenant=_TENANT)
            mock_logger.error.assert_called_once()
            assert "Failed to retrieve" in mock_logger.error.call_args[0][0]
