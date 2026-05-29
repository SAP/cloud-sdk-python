"""Unit tests for Agent Gateway client."""

from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from sap_cloud_sdk.agentgateway import (
    create_client,
    AgentGatewayClient,
    AuthResult,
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
# Test: get_system_auth
# ============================================================


class TestGetSystemAuth:
    """Tests for get_system_auth async method."""

    @pytest.mark.asyncio
    async def test_lob_flow_returns_auth_result(self):
        """Return AuthResult from LoB flow."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.fetch_system_auth",
            new_callable=AsyncMock,
            return_value=("raw-system-jwt-token", "https://agw.example.com"),
        ) as mock_auth:
            agw_client = create_client(tenant_subdomain="my-tenant")

            result = await agw_client.get_system_auth()

            assert isinstance(result, AuthResult)
            assert result.access_token == "raw-system-jwt-token"
            assert result.gateway_url == "https://agw.example.com"
            mock_auth.assert_called_once_with("my-tenant")

    @pytest.mark.asyncio
    async def test_customer_flow_returns_auth_result(self):
        """Return AuthResult from customer flow."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value="/path/to/credentials",
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.load_customer_credentials",
        ) as mock_load, patch(
            "sap_cloud_sdk.agentgateway.agw_client.get_system_token_mtls",
            return_value="customer-system-token",
        ) as mock_mtls:
            mock_creds = MagicMock()
            mock_creds.gateway_url = "https://agw.customer.com"
            mock_load.return_value = mock_creds

            agw_client = create_client()

            result = await agw_client.get_system_auth(app_tid="test-tid")

            assert isinstance(result, AuthResult)
            assert result.access_token == "customer-system-token"
            assert result.gateway_url == "https://agw.customer.com"
            mock_load.assert_called_once_with("/path/to/credentials")
            mock_mtls.assert_called_once_with(mock_creds, 60.0, "test-tid")

    @pytest.mark.asyncio
    async def test_missing_tenant_raises_for_lob(self):
        """Raise AgentGatewaySDKError when tenant_subdomain is missing for LoB."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client()

            with pytest.raises(AgentGatewaySDKError, match="tenant_subdomain is required"):
                await agw_client.get_system_auth()

    @pytest.mark.asyncio
    async def test_callable_tenant_subdomain(self):
        """Accept callable for tenant_subdomain in LoB flow."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.fetch_system_auth",
            new_callable=AsyncMock,
            return_value=("token", "https://agw.example.com"),
        ) as mock_auth:
            get_tenant = lambda: "dynamic-tenant"
            agw_client = create_client(tenant_subdomain=get_tenant)

            await agw_client.get_system_auth()

            mock_auth.assert_called_once_with("dynamic-tenant")

    @pytest.mark.asyncio
    async def test_wraps_unexpected_errors(self):
        """Wrap unexpected errors in AgentGatewaySDKError."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.fetch_system_auth",
            new_callable=AsyncMock,
            side_effect=RuntimeError("unexpected"),
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            with pytest.raises(AgentGatewaySDKError, match="System auth acquisition failed"):
                await agw_client.get_system_auth()


# ============================================================
# Test: get_user_auth
# ============================================================


class TestGetUserAuth:
    """Tests for get_user_auth async method."""

    @pytest.mark.asyncio
    async def test_lob_flow_returns_auth_result(self):
        """Return AuthResult from LoB flow."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
            new_callable=AsyncMock,
            return_value=("raw-user-jwt-token", "https://agw.example.com"),
        ) as mock_auth:
            agw_client = create_client(tenant_subdomain="my-tenant")

            result = await agw_client.get_user_auth(user_token="user-jwt")

            assert isinstance(result, AuthResult)
            assert result.access_token == "raw-user-jwt-token"
            assert result.gateway_url == "https://agw.example.com"
            mock_auth.assert_called_once_with("user-jwt", "my-tenant")

    @pytest.mark.asyncio
    async def test_customer_flow_exchanges_token(self):
        """Exchange token via customer flow and return AuthResult."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value="/path/to/credentials",
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.load_customer_credentials",
        ) as mock_load, patch(
            "sap_cloud_sdk.agentgateway.agw_client.exchange_user_token",
            return_value="exchanged-token",
        ) as mock_exchange:
            mock_creds = MagicMock()
            mock_creds.gateway_url = "https://agw.customer.com"
            mock_load.return_value = mock_creds

            agw_client = create_client()

            result = await agw_client.get_user_auth(
                user_token="user-jwt", app_tid="test-tid"
            )

            assert isinstance(result, AuthResult)
            assert result.access_token == "exchanged-token"
            assert result.gateway_url == "https://agw.customer.com"
            mock_exchange.assert_called_once_with(
                mock_creds, "user-jwt", 60.0, "test-tid"
            )

    @pytest.mark.asyncio
    async def test_missing_user_token_raises(self):
        """Raise AgentGatewaySDKError when user_token is empty."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            with pytest.raises(AgentGatewaySDKError, match="user_token is required"):
                await agw_client.get_user_auth(user_token="")

    @pytest.mark.asyncio
    async def test_callable_user_token(self):
        """Accept callable for user_token."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
            new_callable=AsyncMock,
            return_value=("token", "https://agw.example.com"),
        ) as mock_auth:
            agw_client = create_client(tenant_subdomain="my-tenant")
            get_token = lambda: "dynamic-user-jwt"

            await agw_client.get_user_auth(user_token=get_token)

            mock_auth.assert_called_once_with("dynamic-user-jwt", "my-tenant")

    @pytest.mark.asyncio
    async def test_missing_tenant_raises_for_lob(self):
        """Raise AgentGatewaySDKError when tenant_subdomain is missing for LoB."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            agw_client = create_client()

            with pytest.raises(AgentGatewaySDKError, match="tenant_subdomain is required"):
                await agw_client.get_user_auth(user_token="user-jwt")

    @pytest.mark.asyncio
    async def test_wraps_unexpected_errors(self):
        """Wrap unexpected errors in AgentGatewaySDKError."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
            new_callable=AsyncMock,
            side_effect=RuntimeError("unexpected"),
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            with pytest.raises(AgentGatewaySDKError, match="User auth exchange failed"):
                await agw_client.get_user_auth(user_token="user-jwt")


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
                "sap_cloud_sdk.agentgateway.agw_client.fetch_system_auth",
                new_callable=AsyncMock,
                return_value=("system-token", "https://agw.example.com"),
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

            mock_lob.assert_called_once_with("my-tenant", "system-token", 60.0)

    @pytest.mark.asyncio
    async def test_calls_lob_flow_with_system_token(self):
        """list_mcp_tools should call LoB flow with system token."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.fetch_system_auth",
                new_callable=AsyncMock,
                return_value=("system-token-xyz", "https://agw.example.com"),
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.get_mcp_tools_lob",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_lob,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            await agw_client.list_mcp_tools()

            mock_lob.assert_called_once_with("my-tenant", "system-token-xyz", 60.0)

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
                "sap_cloud_sdk.agentgateway.agw_client.fetch_system_auth",
                new_callable=AsyncMock,
                return_value=("token", "https://agw.example.com"),
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

    @pytest.mark.asyncio
    async def test_customer_flow_passes_system_token(self):
        """Customer flow passes pre-fetched system token to get_mcp_tools_customer."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value="/path/to/credentials",
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.load_customer_credentials",
        ) as mock_load, patch(
            "sap_cloud_sdk.agentgateway.agw_client.get_system_token_mtls",
            return_value="customer-system-token",
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.get_mcp_tools_customer",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_customer:
            mock_creds = MagicMock()
            mock_creds.gateway_url = "https://agw.customer.com"
            mock_load.return_value = mock_creds

            agw_client = create_client()

            await agw_client.list_mcp_tools(app_tid="tid")

            mock_customer.assert_called_once_with(
                mock_creds, "customer-system-token", 60.0
            )


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
                "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
                new_callable=AsyncMock,
                return_value=("exchanged-token", "https://agw.example.com"),
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
                mock_tool, "exchanged-token", 60.0, param1="value1"
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
                "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
                new_callable=AsyncMock,
                return_value=("exchanged-token", "https://agw.example.com"),
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
            mock_lob.assert_called_once_with(mock_tool, "exchanged-token", 60.0)

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
                "sap_cloud_sdk.agentgateway.agw_client.exchange_user_token",
                return_value="exchanged-token",
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_customer",
                new_callable=AsyncMock,
                return_value="customer result",
            ) as mock_customer,
        ):
            mock_creds = MagicMock()
            mock_creds.gateway_url = "https://agw.customer.com"
            mock_load.return_value = mock_creds

            agw_client = create_client(tenant_subdomain="my-tenant")

            result = await agw_client.call_mcp_tool(
                tool=mock_tool,
                user_token="jwt-token",
            )

            assert result == "customer result"
            # load_customer_credentials is called once in get_user_auth()
            mock_load.assert_called_once_with("/path/to/credentials")
            mock_customer.assert_called_once_with(
                mock_tool, "exchanged-token", 60.0
            )

    @pytest.mark.asyncio
    async def test_customer_flow_falls_back_to_system_token(self, mock_tool):
        """Customer flow falls back to system token when user_token is None."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value="/path/to/credentials",
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.load_customer_credentials",
            ) as mock_load,
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.get_system_token_mtls",
                return_value="system-token",
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_customer",
                new_callable=AsyncMock,
                return_value="result with system token",
            ) as mock_customer,
        ):
            mock_creds = MagicMock()
            mock_creds.gateway_url = "https://agw.customer.com"
            mock_load.return_value = mock_creds

            agw_client = create_client()

            result = await agw_client.call_mcp_tool(
                tool=mock_tool,
                user_token=None,
            )

            assert result == "result with system token"
            mock_customer.assert_called_once_with(
                mock_tool, "system-token", 60.0
            )

    @pytest.mark.asyncio
    async def test_calls_lob_flow_with_exchanged_token(self, mock_tool):
        """call_mcp_tool should exchange user token and pass to LoB flow."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
                new_callable=AsyncMock,
                return_value=("exchanged-user-token", "https://agw.example.com"),
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
                mock_tool, "exchanged-user-token", 60.0, order_id="12345"
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
                "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
                new_callable=AsyncMock,
                return_value=("token", "https://agw.example.com"),
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
