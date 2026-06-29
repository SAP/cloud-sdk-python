"""Tests for ExtensibilityClient and create_client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sap_cloud_sdk.extensibility import create_client
from sap_cloud_sdk.extensibility.client import (
    ExtensibilityClient,
    _EXECUTE_WORKFLOW_TOOL_NAME,
    _GET_EXECUTION_TOOL_NAME,
    _N8N_MCP_SERVER_NAME,
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


# ---------------------------------------------------------------------------
# Helpers shared across call_hook tests
# ---------------------------------------------------------------------------

def _make_hook(workflow_id: str = "wf-001", timeout: int = 30) -> Hook:
    return Hook(
        hook_id="agent_pre_hook",
        id="9f6e5f66-7e4f-4ef0-a9f6-e6e1c1220c11",
        n8n_workflow_config=N8nWorkflowConfig(
            workflow_id=workflow_id,
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


def _make_n8n_tool(name: str) -> MCPTool:
    """Return an MCPTool belonging to the N8N MCP server."""
    return MCPTool(
        name=name,
        server_name=_N8N_MCP_SERVER_NAME,
        description="",
        input_schema={},
        url="https://agw.example.com/v1/mcp/sap.btpn8n:apiResource:ManagedN8nMcpServer:v1/gtid-1",
    )


def _make_other_server_tool(name: str) -> MCPTool:
    """Return an MCPTool with the same name but from a different MCP server."""
    return MCPTool(
        name=name,
        server_name="sap.other:apiResource:OtherMcpServer:v1",
        description="",
        input_schema={},
        url="https://agw.example.com/v1/mcp/other/gtid-2",
    )


def _success_payload(workflow_id: str = "wf-001") -> str:
    return json.dumps({
        "status": "success",
        "data": {
            "resultData": {
                "lastNodeExecuted": "Respond to Webhook",
                "runData": {
                    "Respond to Webhook": [
                        {
                            "data": {
                                "main": [
                                    [
                                        {
                                            "json": {
                                                "message_id": "msg-1",
                                                "context_id": "ctx-1",
                                                "role": 2,
                                            }
                                        }
                                    ]
                                ]
                            }
                        }
                    ]
                },
            }
        },
    })


def _running_payload(execution_id: str = "exec-1") -> str:
    return json.dumps({"status": "running", "executionId": execution_id})


def _poll_success_payload() -> str:
    return json.dumps({
        "status": "success",
        "data": {
            "resultData": {
                "lastNodeExecuted": "Respond to Webhook",
                "runData": {
                    "Respond to Webhook": [
                        {
                            "data": {
                                "main": [
                                    [
                                        {
                                            "json": {
                                                "message_id": "msg-2",
                                                "context_id": "ctx-1",
                                                "role": 2,
                                            }
                                        }
                                    ]
                                ]
                            }
                        }
                    ]
                },
            }
        },
    })


def _make_agw_client(tools: list, tool_responses: list) -> MagicMock:
    """Build a mock AgentGatewayClient with preset list_mcp_tools and call_mcp_tool results."""
    agw = MagicMock()
    agw.list_mcp_tools = AsyncMock(return_value=tools)
    agw.call_mcp_tool = AsyncMock(side_effect=tool_responses)
    return agw


# ---------------------------------------------------------------------------
# Tests for ExtensibilityClient.call_hook
# ---------------------------------------------------------------------------


class TestCallHook:
    """Tests for ExtensibilityClient.call_hook (async, AGW-based)."""

    def _make_client(self, agw: MagicMock) -> ExtensibilityClient:
        """Build an ExtensibilityClient with a mock transport and patched AGW factory."""
        return ExtensibilityClient(MagicMock())

    @pytest.mark.asyncio
    async def test_execute_tool_not_found_raises(self):
        """Raises ExtensibilityError when execute_workflow tool is absent."""
        agw = _make_agw_client(tools=[], tool_responses=[])
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            with pytest.raises(ExtensibilityError, match=_EXECUTE_WORKFLOW_TOOL_NAME):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_get_exec_tool_not_found_raises(self):
        """Raises ExtensibilityError when get_execution tool is absent."""
        tools = [_make_n8n_tool(_EXECUTE_WORKFLOW_TOOL_NAME)]
        agw = _make_agw_client(tools=tools, tool_responses=[])
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            with pytest.raises(ExtensibilityError, match=_GET_EXECUTION_TOOL_NAME):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_composite_key_ignores_wrong_server(self):
        """Tools from a different server with the same names must not match."""
        tools = [
            _make_other_server_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_other_server_tool(_GET_EXECUTION_TOOL_NAME),
        ]
        agw = _make_agw_client(tools=tools, tool_responses=[])
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            with pytest.raises(ExtensibilityError, match=_EXECUTE_WORKFLOW_TOOL_NAME):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_composite_key_picks_correct_tool_among_duplicates(self):
        """Picks the N8N tool when another server exposes identically-named tools."""
        tools = [
            _make_other_server_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_other_server_tool(_GET_EXECUTION_TOOL_NAME),
            _make_n8n_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_n8n_tool(_GET_EXECUTION_TOOL_NAME),
        ]
        agw = _make_agw_client(
            tools=tools,
            tool_responses=[_running_payload(), _poll_success_payload()],
        )
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ), patch(
            "sap_cloud_sdk.extensibility.client.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")
        assert result is not None
        # Both tool calls must have used the N8N server tools, not the other one
        for call in agw.call_mcp_tool.call_args_list:
            assert call[0][0].server_name == _N8N_MCP_SERVER_NAME

    @pytest.mark.asyncio
    async def test_success_synchronous(self):
        """Returns a Message when get_execution responds with status=success."""
        tools = [
            _make_n8n_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_n8n_tool(_GET_EXECUTION_TOOL_NAME),
        ]
        agw = _make_agw_client(
            tools=tools,
            tool_responses=[_running_payload(), _poll_success_payload()],
        )
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ), patch(
            "sap_cloud_sdk.extensibility.client.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")
        assert result is not None
        assert result.message_id == "msg-2"
        assert agw.call_mcp_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_success_after_polling(self):
        """Returns a Message after one poll round via get_execution."""
        tools = [
            _make_n8n_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_n8n_tool(_GET_EXECUTION_TOOL_NAME),
        ]
        agw = _make_agw_client(
            tools=tools,
            tool_responses=[_running_payload(), _poll_success_payload()],
        )
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ), patch(
            "sap_cloud_sdk.extensibility.client.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")
        assert result is not None
        assert result.message_id == "msg-2"
        assert agw.call_mcp_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_terminal_status_from_execute_raises(self):
        """Raises ExtensibilityError on a terminal status from execute_workflow."""
        tools = [
            _make_n8n_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_n8n_tool(_GET_EXECUTION_TOOL_NAME),
        ]
        terminal_payload = json.dumps({"status": "error", "error": "workflow crashed"})
        agw = _make_agw_client(tools=tools, tool_responses=[terminal_payload])
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            with pytest.raises(ExtensibilityError, match="workflow crashed"):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_terminal_status_from_poll_raises(self):
        """Raises ExtensibilityError on a terminal status from get_execution poll."""
        tools = [
            _make_n8n_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_n8n_tool(_GET_EXECUTION_TOOL_NAME),
        ]
        poll_terminal = json.dumps({"status": "error", "error": "node failed"})
        agw = _make_agw_client(
            tools=tools,
            tool_responses=[_running_payload(), poll_terminal],
        )
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ), patch(
            "sap_cloud_sdk.extensibility.client.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            with pytest.raises(ExtensibilityError, match="node failed"):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_timeout_raises(self):
        """Raises ExtensibilityError when deadline is exceeded without a success status."""
        tools = [
            _make_n8n_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_n8n_tool(_GET_EXECUTION_TOOL_NAME),
        ]
        # Always returns "running" so the loop never exits via success/terminal
        agw = _make_agw_client(
            tools=tools,
            tool_responses=[_running_payload()] + [_running_payload()] * 100,
        )
        client = self._make_client(agw)
        # Use a hook with timeout=0 so monotonic deadline is immediately exceeded
        hook = _make_hook(timeout=0)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ), patch(
            "sap_cloud_sdk.extensibility.client.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            with pytest.raises(ExtensibilityError, match="timed out"):
                await client.call_hook_agw(hook=hook, tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_agw_call_mcp_tool_exception_raises_transport_error(self):
        """Wraps call_mcp_tool exceptions in TransportError."""
        tools = [
            _make_n8n_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_n8n_tool(_GET_EXECUTION_TOOL_NAME),
        ]
        agw = MagicMock()
        agw.list_mcp_tools = AsyncMock(return_value=tools)
        agw.call_mcp_tool = AsyncMock(side_effect=RuntimeError("network error"))
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ):
            with pytest.raises(TransportError, match="network error"):
                await client.call_hook_agw(hook=_make_hook(), tenant_subdomain="t")

    @pytest.mark.asyncio
    async def test_workflow_id_passed_to_execute_tool(self):
        """Verifies the correct workflowId is forwarded to call_mcp_tool."""
        tools = [
            _make_n8n_tool(_EXECUTE_WORKFLOW_TOOL_NAME),
            _make_n8n_tool(_GET_EXECUTION_TOOL_NAME),
        ]
        agw = _make_agw_client(
            tools=tools,
            tool_responses=[_running_payload(), _poll_success_payload()],
        )
        client = self._make_client(agw)
        with patch(
            "sap_cloud_sdk.extensibility.client.create_agw_client",
            return_value=agw,
        ), patch(
            "sap_cloud_sdk.extensibility.client.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await client.call_hook_agw(
                hook=_make_hook(workflow_id="wf-xyz"), tenant_subdomain="t"
            )
        # First call is execute_workflow — check workflowId was forwarded correctly
        first_call_kwargs = agw.call_mcp_tool.call_args_list[0][1]
        assert first_call_kwargs["workflowId"] == "wf-xyz"
