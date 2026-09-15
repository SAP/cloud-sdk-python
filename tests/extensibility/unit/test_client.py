"""Tests for ExtensibilityClient and create_client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sap_cloud_sdk.extensibility import create_client
from sap_cloud_sdk.extensibility.client import (
    ExtensibilityClient,
    _EXECUTE_WORKFLOW_TOOL_NAME,
    _GET_EXECUTION_TOOL_NAME,
)
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
from sap_cloud_sdk.extensibility.exceptions import ExtensibilityError, TransportError
from sap_cloud_sdk.agentgateway._models import MCPTool


# ---------------------------------------------------------------------------
# Shared constants for hook tool identity
# ---------------------------------------------------------------------------

_TOOL_NAME = "convertCurrency"
_CARD_ORD_ID = "sap.n8nwfrt:apiResource:invoice-po-solution_currency-conversion.convertCurrency_mcp:v1"
_ORD_ID = "sap.n8nwfrt:apiResource:invoice-po-solution_currency-conversion.convertCurrency:v1"
_GLOBAL_TENANT_ID = "tenant-example-001"


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
                        ord_id=_ORD_ID,
                        card_ord_id=_CARD_ORD_ID,
                        tool_name=_TOOL_NAME,
                        global_tenant_id=_GLOBAL_TENANT_ID,
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
                        ord_id=_ORD_ID,
                        card_ord_id=_CARD_ORD_ID,
                        tool_name=_TOOL_NAME,
                        global_tenant_id=_GLOBAL_TENANT_ID,
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


# ---------------------------------------------------------------------------
# Helpers shared across call_hook_agw tests
# ---------------------------------------------------------------------------

def _make_hook(
    tool_name: str = _TOOL_NAME,
    card_ord_id: str = _CARD_ORD_ID,
    timeout: int = 30,
) -> Hook:
    return Hook(
        hook_id="agent_pre_hook",
        id="9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
        n8n_workflow_config=N8nWorkflowConfig(
            ord_id=_ORD_ID,
            card_ord_id=card_ord_id,
            tool_name=tool_name,
            global_tenant_id=_GLOBAL_TENANT_ID,
            method=HTTPMethod.POST,
        ),
        name="Pre Hook",
        type=HookType.BEFORE,
        deployment_type=DeploymentType.N8N,
        timeout=timeout,
        execution_mode=ExecutionMode.SYNC,
        on_failure=OnFailure.CONTINUE,
        order=0,
        can_short_circuit=True,
    )


def _make_hook_tool(
    tool_name: str = _TOOL_NAME,
    card_ord_id: str = _CARD_ORD_ID,
) -> MCPTool:
    """Return an MCPTool matching the hook's tool_name and card_ord_id."""
    return MCPTool(
        name=tool_name,
        server_name=card_ord_id,
        description="",
        input_schema={},
        url="https://agw.example.com/v1/mcp/sap.n8nwfrt.../gtid-1",
    )


def _make_other_server_tool(tool_name: str = _TOOL_NAME) -> MCPTool:
    """Return an MCPTool with the same tool name but from a different MCP server."""
    return MCPTool(
        name=tool_name,
        server_name="sap.other:apiResource:OtherServer:v1",
        description="",
        input_schema={},
        url="https://agw.example.com/v1/mcp/other/gtid-2",
    )


def _success_payload() -> str:
    """A2A Message returned directly by the n8n MCP translation card."""
    return json.dumps({
        "messageId": "msg-1",
        "role": "agent",
        "parts": [{"kind": "text", "text": "Currency converted successfully."}],
    })


def _make_agw_client(tools: list, tool_responses: list) -> MagicMock:
    """Build a mock AgentGatewayClient with preset list_mcp_tools and call_mcp_tool results."""
    agw = MagicMock()
    agw.list_mcp_tools = AsyncMock(return_value=tools)
    agw.call_mcp_tool = AsyncMock(side_effect=tool_responses)
    return agw


# ---------------------------------------------------------------------------
# Tests for ExtensibilityClient.call_hook_agw
# ---------------------------------------------------------------------------


class TestCallHookAgw:
    """Tests for ExtensibilityClient.call_hook_agw (AGW-based MCP invocation)."""

    def _make_client(self) -> ExtensibilityClient:
        return ExtensibilityClient(MagicMock())

    @pytest.mark.asyncio
    async def test_tool_not_found_raises(self):
        """Raises ExtensibilityError when no tool matches tool_name + card_ord_id."""
        agw = _make_agw_client(tools=[], tool_responses=[])
        client = self._make_client()
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            with pytest.raises(ExtensibilityError, match=_TOOL_NAME):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_wrong_server_does_not_match(self):
        """A tool with the right name but wrong server_name must not match."""
        agw = _make_agw_client(tools=[_make_other_server_tool()], tool_responses=[])
        client = self._make_client()
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            with pytest.raises(ExtensibilityError, match=_TOOL_NAME):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_success_returns_message(self):
        """Returns a Message on a successful single tool call."""
        agw = _make_agw_client(tools=[_make_hook_tool()], tool_responses=[_success_payload()])
        client = self._make_client()
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            result = await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")
        assert result is not None
        assert result.message_id == "msg-1"
        assert agw.call_mcp_tool.call_count == 1

    @pytest.mark.asyncio
    async def test_picks_correct_tool_among_duplicates(self):
        """Picks the hook's card tool when another server exposes an identically-named tool."""
        tools = [_make_other_server_tool(), _make_hook_tool()]
        agw = _make_agw_client(tools=tools, tool_responses=[_success_payload()])
        client = self._make_client()
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            result = await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")
        assert result is not None
        assert agw.call_mcp_tool.call_args[0][0].server_name == _CARD_ORD_ID

    @pytest.mark.asyncio
    async def test_agw_call_exception_raises_transport_error(self):
        """Wraps call_mcp_tool exceptions in TransportError."""
        agw = MagicMock()
        agw.list_mcp_tools = AsyncMock(return_value=[_make_hook_tool()])
        agw.call_mcp_tool = AsyncMock(side_effect=RuntimeError("network error"))
        client = self._make_client()
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            with pytest.raises(TransportError, match="network error"):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_non_a2a_response_raises_extensibility_error(self):
        """Raises ExtensibilityError when the tool response is not a valid A2A Message."""
        bad_payload = json.dumps({"not": "a2a"})
        agw = _make_agw_client(tools=[_make_hook_tool()], tool_responses=[bad_payload])
        client = self._make_client()
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            with pytest.raises(ExtensibilityError, match="A2A"):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_webhook_inputs_forwarded_to_tool(self):
        """Verifies webhook payload structure is forwarded correctly to call_mcp_tool."""
        agw = _make_agw_client(tools=[_make_hook_tool()], tool_responses=[_success_payload()])
        client = self._make_client()
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")
        call_kwargs = agw.call_mcp_tool.call_args[1]
        assert "inputs" in call_kwargs
        assert call_kwargs["inputs"]["type"] == "webhook"
        assert "webhookData" in call_kwargs["inputs"]
        assert call_kwargs["inputs"]["webhookData"]["method"] == HTTPMethod.POST
