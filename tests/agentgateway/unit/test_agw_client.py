"""Unit tests for Agent Gateway client."""

from unittest.mock import patch, AsyncMock

import pytest

from sap_cloud_sdk.agentgateway import (
    create_client,
    AgentGatewayClient,
    MCPTool,
    AgentGatewaySDKError,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_tool():
    """Create a mock MCPTool."""
    return MCPTool(
        name="test-tool",
        server_name="test-server",
        description="A test tool",
        input_schema={},
        url="https://example.com/mcp",
        fragment_name="test-fragment",
    )


# ============================================================
# Test: create_client factory
# ============================================================


class TestCreateClient:
    """Tests for create_client factory function."""

    def test_returns_agentgatewayclient(self):
        """create_client should return an AgentGatewayClient instance."""
        agw_client = create_client(tenant_subdomain="my-tenant")
        assert isinstance(agw_client, AgentGatewayClient)

    def test_accepts_callable_tenant(self):
        """create_client should accept callable for tenant_subdomain."""
        get_tenant = lambda: "my-tenant"
        agw_client = create_client(tenant_subdomain=get_tenant)
        assert isinstance(agw_client, AgentGatewayClient)

    def test_accepts_none_tenant(self):
        """create_client should accept None for tenant_subdomain."""
        agw_client = create_client()
        assert isinstance(agw_client, AgentGatewayClient)


# ============================================================
# Test: AgentGatewayClient._resolve_value
# ============================================================


class TestResolveValue:
    """Tests for AgentGatewayClient._resolve_value static method."""

    def test_resolves_string(self):
        """_resolve_value should return string as-is."""
        result = AgentGatewayClient._resolve_value("my-value", "error")
        assert result == "my-value"

    def test_resolves_callable(self):
        """_resolve_value should call callable and return result."""
        get_value = lambda: "from-callable"
        result = AgentGatewayClient._resolve_value(get_value, "error")
        assert result == "from-callable"

    def test_raises_on_none(self):
        """_resolve_value should raise on None."""
        with pytest.raises(AgentGatewaySDKError, match="test error"):
            AgentGatewayClient._resolve_value(None, "test error")

    def test_raises_on_empty_string(self):
        """_resolve_value should raise on empty string."""
        with pytest.raises(AgentGatewaySDKError, match="test error"):
            AgentGatewayClient._resolve_value("", "test error")

    def test_raises_on_whitespace_string(self):
        """_resolve_value should raise on whitespace-only string."""
        with pytest.raises(AgentGatewaySDKError, match="test error"):
            AgentGatewayClient._resolve_value("   ", "test error")

    def test_raises_on_callable_returning_empty(self):
        """_resolve_value should raise if callable returns empty."""
        get_empty = lambda: ""
        with pytest.raises(AgentGatewaySDKError, match="test error"):
            AgentGatewayClient._resolve_value(get_empty, "test error")


# ============================================================
# Test: list_mcp_tools
# ============================================================


class TestListMcpTools:
    """Tests for list_mcp_tools async method."""

    @pytest.mark.asyncio
    async def test_missing_tenant_subdomain_raises(self):
        """Raise AgentGatewaySDKError when tenant_subdomain is missing for LoB flow."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client()

            with pytest.raises(
                AgentGatewaySDKError, match="tenant_subdomain is required"
            ):
                await agw_client.list_mcp_tools()

    @pytest.mark.asyncio
    async def test_empty_tenant_subdomain_raises(self):
        """Raise AgentGatewaySDKError when tenant_subdomain is empty."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client(tenant_subdomain="")

            with pytest.raises(
                AgentGatewaySDKError, match="tenant_subdomain is required"
            ):
                await agw_client.list_mcp_tools()

    @pytest.mark.asyncio
    async def test_whitespace_tenant_subdomain_raises(self):
        """Raise AgentGatewaySDKError when tenant_subdomain is whitespace only."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client(tenant_subdomain="   ")

            with pytest.raises(
                AgentGatewaySDKError, match="tenant_subdomain is required"
            ):
                await agw_client.list_mcp_tools()

    @pytest.mark.asyncio
    async def test_with_callable_tenant(self):
        """Accept callable for tenant_subdomain."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.get_mcp_tools_lob",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_lob,
        ):
            get_tenant = lambda: "my-tenant"
            agw_client = create_client(tenant_subdomain=get_tenant)

            await agw_client.list_mcp_tools()

            mock_lob.assert_called_once_with("my-tenant")

    @pytest.mark.asyncio
    async def test_calls_lob_flow(self):
        """list_mcp_tools should call LoB flow with correct parameters."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.get_mcp_tools_lob",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_lob,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            await agw_client.list_mcp_tools()

            mock_lob.assert_called_once_with("my-tenant")

    @pytest.mark.asyncio
    async def test_returns_tools_from_lob_flow(self):
        """Return tools from LoB flow."""
        mock_tools = [
            MCPTool(
                name="tool1",
                server_name="server",
                description="Tool 1",
                input_schema={},
                url="https://example.com",
                fragment_name="fragment",
            )
        ]

        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.get_mcp_tools_lob",
                new_callable=AsyncMock,
                return_value=mock_tools,
            ),
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            result = await agw_client.list_mcp_tools()

            assert result == mock_tools
            assert len(result) == 1
            assert result[0].name == "tool1"


# ============================================================
# Test: call_mcp_tool
# ============================================================


class TestCallMcpTool:
    """Tests for call_mcp_tool method on AgentGatewayClient."""

    @pytest.mark.asyncio
    async def test_missing_user_token_raises(self, mock_tool):
        """Raise AgentGatewaySDKError when user_token is missing for LoB flow."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            with pytest.raises(AgentGatewaySDKError, match="user_token is required"):
                await agw_client.call_mcp_tool(tool=mock_tool, user_token="")

    @pytest.mark.asyncio
    async def test_whitespace_user_token_raises(self, mock_tool):
        """Raise AgentGatewaySDKError when user_token is whitespace only."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            with pytest.raises(AgentGatewaySDKError, match="user_token is required"):
                await agw_client.call_mcp_tool(tool=mock_tool, user_token="   ")

    @pytest.mark.asyncio
    async def test_missing_tenant_subdomain_raises(self, mock_tool):
        """Raise AgentGatewaySDKError when tenant_subdomain is missing for LoB flow."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client()

            with pytest.raises(
                AgentGatewaySDKError, match="tenant_subdomain is required"
            ):
                await agw_client.call_mcp_tool(tool=mock_tool, user_token="jwt-token")

    @pytest.mark.asyncio
    async def test_empty_tenant_subdomain_raises(self, mock_tool):
        """Raise AgentGatewaySDKError when tenant_subdomain is empty."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client(tenant_subdomain="")

            with pytest.raises(
                AgentGatewaySDKError, match="tenant_subdomain is required"
            ):
                await agw_client.call_mcp_tool(tool=mock_tool, user_token="jwt-token")

    @pytest.mark.asyncio
    async def test_with_callable_user_token(self, mock_tool):
        """Accept callable for user_token."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_lob",
                new_callable=AsyncMock,
                return_value="result",
            ) as mock_lob,
        ):
            get_token = lambda: "my-jwt"
            agw_client = create_client(tenant_subdomain="my-tenant")

            result = await agw_client.call_mcp_tool(
                tool=mock_tool,
                user_token=get_token,
                param1="value1",
            )

            assert result == "result"
            mock_lob.assert_called_once_with(
                mock_tool, "my-jwt", "my-tenant", param1="value1"
            )

    @pytest.mark.asyncio
    async def test_with_callable_tenant_subdomain(self, mock_tool):
        """Accept callable for tenant_subdomain."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_lob",
                new_callable=AsyncMock,
                return_value="result",
            ) as mock_lob,
        ):
            get_tenant = lambda: "my-tenant"
            agw_client = create_client(tenant_subdomain=get_tenant)

            result = await agw_client.call_mcp_tool(
                tool=mock_tool,
                user_token="my-jwt",
            )

            assert result == "result"
            mock_lob.assert_called_once_with(mock_tool, "my-jwt", "my-tenant")

    @pytest.mark.asyncio
    async def test_customer_credentials_calls_customer_flow(self, mock_tool):
        """Call customer flow when customer credentials are detected."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value="/path/to/credentials",
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.load_customer_credentials",
            ) as mock_load,
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_customer",
                new_callable=AsyncMock,
                return_value="customer result",
            ) as mock_customer,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            result = await agw_client.call_mcp_tool(
                tool=mock_tool,
                user_token="jwt-token",
            )

            assert result == "customer result"
            mock_load.assert_called_once_with("/path/to/credentials")
            mock_customer.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_lob_flow(self, mock_tool):
        """call_mcp_tool should call LoB flow with correct parameters."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_lob",
                new_callable=AsyncMock,
                return_value="tool result",
            ) as mock_lob,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            result = await agw_client.call_mcp_tool(
                tool=mock_tool,
                user_token="jwt-token",
                order_id="12345",
            )

            assert result == "tool result"
            mock_lob.assert_called_once_with(
                mock_tool, "jwt-token", "my-tenant", order_id="12345"
            )

    @pytest.mark.asyncio
    async def test_returns_result_from_lob_flow(self, mock_tool):
        """Return result from LoB flow."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_lob",
                new_callable=AsyncMock,
                return_value="Success: Order created",
            ),
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            result = await agw_client.call_mcp_tool(
                tool=mock_tool,
                user_token="jwt-token",
            )

            assert result == "Success: Order created"
