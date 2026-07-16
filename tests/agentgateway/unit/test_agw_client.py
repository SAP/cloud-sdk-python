"""Unit tests for Agent Gateway client."""

from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from sap_cloud_sdk.agentgateway import (
    create_client,
    AgentGatewayClient,
    Agent,
    AgentCard,
    AgentCardFilter,
    AuthResult,
    MCPTool,
    AgentGatewaySDKError,
)

from sap_cloud_sdk.agentgateway._implicit_auditlog import (
    send_audit_event_invoked,
    send_audit_event_completed,
    send_audit_event_failed,
    MCP_TOOL_INVOKED,
    MCP_TOOL_COMPLETED,
    MCP_TOOL_FAILED,
)
from sap_cloud_sdk.agentgateway.config import AuditLogMode, ClientConfig
from sap_cloud_sdk.core.telemetry import Module

_TENANT_UUID = "9e0d89c9-17cd-439d-8a8b-9c44d3d272f0"


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


def _client_token_cache(client: AgentGatewayClient):
    """Access the client-owned token cache for white-box tests."""
    return getattr(client, "_token_cache")


def _client_gateway_url_cache(client: AgentGatewayClient):
    """Access the client-owned gateway URL cache for white-box tests."""
    return getattr(client, "_gateway_url_cache")


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
            token_cache = _client_token_cache(agw_client)
            gateway_url_cache = _client_gateway_url_cache(agw_client)

            result = await agw_client.get_system_auth()

            assert isinstance(result, AuthResult)
            assert result.access_token == "raw-system-jwt-token"
            assert result.gateway_url == "https://agw.example.com"
            mock_auth.assert_called_once_with(
                "my-tenant",
                token_cache=token_cache,
                gateway_url_cache=gateway_url_cache,
            )

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
            token_cache = _client_token_cache(agw_client)

            result = await agw_client.get_system_auth(app_tid="test-tid")

            assert isinstance(result, AuthResult)
            assert result.access_token == "customer-system-token"
            assert result.gateway_url == "https://agw.customer.com"
            mock_load.assert_called_once_with("/path/to/credentials")
            mock_mtls.assert_called_once_with(
                mock_creds, 60.0, "test-tid", token_cache
            )

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
            token_cache = _client_token_cache(agw_client)
            gateway_url_cache = _client_gateway_url_cache(agw_client)

            await agw_client.get_system_auth()

            mock_auth.assert_called_once_with(
                "dynamic-tenant",
                token_cache=token_cache,
                gateway_url_cache=gateway_url_cache,
            )

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
            token_cache = _client_token_cache(agw_client)
            gateway_url_cache = _client_gateway_url_cache(agw_client)

            result = await agw_client.get_user_auth(user_token="user-jwt")

            assert isinstance(result, AuthResult)
            assert result.access_token == "raw-user-jwt-token"
            assert result.gateway_url == "https://agw.example.com"
            mock_auth.assert_called_once_with(
                "user-jwt",
                "my-tenant",
                token_cache=token_cache,
                gateway_url_cache=gateway_url_cache,
            )

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
            token_cache = _client_token_cache(agw_client)

            result = await agw_client.get_user_auth(
                user_token="user-jwt", app_tid="test-tid"
            )

            assert isinstance(result, AuthResult)
            assert result.access_token == "exchanged-token"
            assert result.gateway_url == "https://agw.customer.com"
            mock_exchange.assert_called_once_with(
                mock_creds, "user-jwt", 60.0, "test-tid", token_cache
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
            token_cache = _client_token_cache(agw_client)
            gateway_url_cache = _client_gateway_url_cache(agw_client)

            await agw_client.get_user_auth(user_token=get_token)

            mock_auth.assert_called_once_with(
                "dynamic-user-jwt",
                "my-tenant",
                token_cache=token_cache,
                gateway_url_cache=gateway_url_cache,
            )

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

    @pytest.mark.asyncio
    async def test_lob_flow_with_user_token_uses_user_auth(self):
        """LoB flow uses user auth when user_token is provided."""
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
                new_callable=AsyncMock,
                return_value=("user-token-xyz", "https://agw.example.com"),
            ) as mock_user_auth,
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.get_mcp_tools_lob",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_lob,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")

            await agw_client.list_mcp_tools(user_token="user-jwt")

            mock_user_auth.assert_called_once()
            mock_lob.assert_called_once_with("my-tenant", "user-token-xyz", 60.0)

    @pytest.mark.asyncio
    async def test_customer_flow_with_user_token_uses_user_auth(self):
        """Customer flow uses user auth when user_token is provided."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value="/path/to/credentials",
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.load_customer_credentials",
        ) as mock_load, patch(
            "sap_cloud_sdk.agentgateway.agw_client.exchange_user_token",
            return_value="exchanged-user-token",
        ), patch(
            "sap_cloud_sdk.agentgateway.agw_client.get_mcp_tools_customer",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_customer:
            mock_creds = MagicMock()
            mock_creds.gateway_url = "https://agw.customer.com"
            mock_load.return_value = mock_creds

            agw_client = create_client()

            await agw_client.list_mcp_tools(user_token="user-jwt", app_tid="tid")

            mock_customer.assert_called_once_with(
                mock_creds, "exchanged-user-token", 60.0
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


# ============================================================
# Test: list_agent_cards
# ============================================================


class TestListAgentCards:
    """Tests for list_agent_cards async method."""

    @pytest.mark.asyncio
    async def test_returns_agents_from_lob_flow(self):
        """Return list of Agent objects from LoB flow."""
        card = AgentCard(raw={"name": "TestAgent"})
        agent = Agent(ord_id="sap.s4:agent:v1", agent_card=card)

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
                "sap_cloud_sdk.agentgateway.agw_client.get_agent_cards_lob",
                new_callable=AsyncMock,
                return_value=[agent],
            ) as mock_lob,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")
            result = await agw_client.list_agent_cards()

        assert result == [agent]
        mock_lob.assert_called_once_with(
            "my-tenant",
            "system-token",
            60.0,
            agent_names=None,
            ord_ids=None,
        )

    @pytest.mark.asyncio
    async def test_passes_filter_arguments(self):
        """Pass names and ord_ids from AgentCardFilter through to get_agent_cards_lob."""
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
                "sap_cloud_sdk.agentgateway.agw_client.get_agent_cards_lob",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_lob,
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")
            await agw_client.list_agent_cards(
                filter=AgentCardFilter(agent_names=["Billing Agent"], ord_ids=["sap.s4:agent:v1"])
            )

        mock_lob.assert_called_once_with(
            "my-tenant",
            "token",
            60.0,
            agent_names=["Billing Agent"],
            ord_ids=["sap.s4:agent:v1"],
        )

    @pytest.mark.asyncio
    async def test_raises_for_customer_agent_flow(self):
        """Raise AgentGatewaySDKError when called from a customer agent (not yet supported)."""
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value="/path/to/credentials",
        ):
            agw_client = create_client()
            with pytest.raises(AgentGatewaySDKError, match="not yet supported for customer agents"):
                await agw_client.list_agent_cards()

    @pytest.mark.asyncio
    async def test_raises_when_tenant_subdomain_missing(self):
        """Raise AgentGatewaySDKError when tenant_subdomain is not provided."""
        agw_client = create_client()
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value=None,
        ):
            with pytest.raises(AgentGatewaySDKError, match="tenant_subdomain"):
                await agw_client.list_agent_cards()

    @pytest.mark.asyncio
    async def test_propagates_sdk_error(self):
        """Re-raise AgentGatewaySDKError from get_agent_cards_lob."""
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
                "sap_cloud_sdk.agentgateway.agw_client.get_agent_cards_lob",
                new_callable=AsyncMock,
                side_effect=AgentGatewaySDKError("fragment discovery failed"),
            ),
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")
            with pytest.raises(AgentGatewaySDKError, match="fragment discovery failed"):
                await agw_client.list_agent_cards()

    @pytest.mark.asyncio
    async def test_wraps_unexpected_error(self):
        """Wrap unexpected errors in AgentGatewaySDKError."""
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
                "sap_cloud_sdk.agentgateway.agw_client.get_agent_cards_lob",
                new_callable=AsyncMock,
                side_effect=RuntimeError("unexpected"),
            ),
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")
            with pytest.raises(AgentGatewaySDKError, match="Agent card discovery failed"):
                await agw_client.list_agent_cards()


# ============================================================
# Test: _telemetry_source wiring
# ============================================================


class TestCreateClientTelemetrySource:
    """Verify _telemetry_source kwarg is stored on the AgentGatewayClient."""

    def test_default_source_is_none(self):
        agw_client = create_client(tenant_subdomain="my-tenant")
        assert agw_client._telemetry_source is None

    def test_explicit_source_is_stored(self):
        agw_client = create_client(
            tenant_subdomain="my-tenant",
            _telemetry_source=Module.EXTENSIBILITY,
        )
        assert agw_client._telemetry_source is Module.EXTENSIBILITY


# ============================================================
# Test: get_ias_client_id
# ============================================================


_DEST_CREATE_PATCH = "sap_cloud_sdk.destination.create_client"
_IAS_DEST_NAME_PATCH = "sap_cloud_sdk.agentgateway._lob._ias_dest_name"
_GET_IAS_CLIENT_ID_LOB_PATCH = "sap_cloud_sdk.agentgateway.agw_client.get_ias_client_id_lob"
_DETECT_CREDS_PATCH = "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials"
_LOAD_CREDS_PATCH = "sap_cloud_sdk.agentgateway.agw_client.load_customer_credentials"

_NO_CUSTOMER_CREDS = patch(_DETECT_CREDS_PATCH, return_value=None)


class TestGetIasClientId:
    """Tests for AgentGatewayClient.get_ias_client_id()."""

    # --- Customer flow ---

    def test_customer_returns_client_id_from_credentials(self):
        mock_creds = MagicMock()
        mock_creds.client_id = "customer-client-id"

        with (
            patch(_DETECT_CREDS_PATCH, return_value="/etc/ums/credentials/credentials"),
            patch(_LOAD_CREDS_PATCH, return_value=mock_creds),
        ):
            result = create_client().get_ias_client_id()

        assert result == "customer-client-id"

    def test_customer_raises_on_load_failure(self):
        with (
            patch(_DETECT_CREDS_PATCH, return_value="/etc/ums/credentials/credentials"),
            patch(_LOAD_CREDS_PATCH, side_effect=Exception("parse error")),
        ):
            with pytest.raises(AgentGatewaySDKError, match="Could not resolve IAS client ID"):
                create_client().get_ias_client_id()

    # --- LoB flow ---

    @_NO_CUSTOMER_CREDS
    def test_lob_returns_client_id_from_destination_properties(self, _mock_detect):
        with patch(_GET_IAS_CLIENT_ID_LOB_PATCH, return_value="lob-client-id"):
            result = create_client(tenant_subdomain="my-tenant").get_ias_client_id()

        assert result == "lob-client-id"

    @_NO_CUSTOMER_CREDS
    def test_lob_raises_when_destination_not_found(self, _mock_detect):
        with patch(_GET_IAS_CLIENT_ID_LOB_PATCH, side_effect=AgentGatewaySDKError("IAS destination 'sap-managed-runtime-ias-eu10' not found")):
            with pytest.raises(AgentGatewaySDKError, match="IAS destination"):
                create_client(tenant_subdomain="my-tenant").get_ias_client_id()

    @_NO_CUSTOMER_CREDS
    def test_lob_returns_empty_string_when_property_absent(self, _mock_detect):
        with patch(_GET_IAS_CLIENT_ID_LOB_PATCH, return_value=""):
            result = create_client(tenant_subdomain="my-tenant").get_ias_client_id()

        assert result == ""

    @_NO_CUSTOMER_CREDS
    def test_lob_raises_on_exception(self, _mock_detect):
        with patch(_GET_IAS_CLIENT_ID_LOB_PATCH, side_effect=EnvironmentError("APPFND_CONHOS_LANDSCAPE not set")):
            with pytest.raises(AgentGatewaySDKError, match="Could not resolve IAS client ID"):
                create_client(tenant_subdomain="my-tenant").get_ias_client_id()


# ============================================================
# Test: send_audit_event_invoked / completed / failed
# ============================================================


class TestSendAuditEventInvoked:
    """Tests for send_audit_event_invoked helper."""

    def test_no_op_without_audit_client(self):
        """send_audit_event_invoked is a no-op when audit_client is None."""
        send_audit_event_invoked(None, "tool-name", "user@example.com")

    def test_no_op_without_tenant_id(self):
        """send_audit_event_invoked is a no-op when get_tenant_id returns empty string."""
        mock_audit = MagicMock()
        with patch(
            "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
            return_value="",
        ):
            send_audit_event_invoked(mock_audit, "tool-name")
        mock_audit.send.assert_not_called()

    def test_sends_invoked_event(self):
        """send_audit_event_invoked builds and sends a ZzzCustomEvent with MCP_TOOL_INVOKED."""
        mock_audit = MagicMock()
        with patch(
            "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
            return_value=_TENANT_UUID,
        ):
            send_audit_event_invoked(mock_audit, "my-tool", "user@example.com")
        mock_audit.send.assert_called_once()
        event = mock_audit.send.call_args[0][0]
        assert event.common.tenant_id == _TENANT_UUID
        assert event.common.user_initiator_id == "user@example.com"
        assert event.common.app_context["event_name"] == MCP_TOOL_INVOKED

    def test_sends_without_user_id(self):
        """send_audit_event_invoked omits user_initiator_id when user_id is None."""
        mock_audit = MagicMock()
        with patch(
            "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
            return_value=_TENANT_UUID,
        ):
            send_audit_event_invoked(mock_audit, "my-tool")
        event = mock_audit.send.call_args[0][0]
        assert event.common.user_initiator_id == ""

    def test_best_effort_suppresses_send_errors(self):
        """send_audit_event_invoked does not propagate exceptions in BEST_EFFORT mode."""
        mock_audit = MagicMock()
        mock_audit.send.side_effect = RuntimeError("send failed")
        with patch(
            "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
            return_value=_TENANT_UUID,
        ):
            send_audit_event_invoked(mock_audit, "my-tool", mode=AuditLogMode.BEST_EFFORT)

    def test_strict_raises_on_send_error(self):
        """send_audit_event_invoked raises in STRICT mode when send fails."""
        mock_audit = MagicMock()
        mock_audit.send.side_effect = RuntimeError("send failed")
        with (
            patch(
                "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
                return_value=_TENANT_UUID,
            ),
            pytest.raises(RuntimeError, match="send failed"),
        ):
            send_audit_event_invoked(mock_audit, "my-tool", mode=AuditLogMode.STRICT)

    def test_disabled_skips_send(self):
        """send_audit_event_invoked does nothing in DISABLED mode."""
        mock_audit = MagicMock()
        with patch(
            "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
            return_value=_TENANT_UUID,
        ):
            send_audit_event_invoked(mock_audit, "my-tool", mode=AuditLogMode.DISABLED)
        mock_audit.send.assert_not_called()


class TestSendAuditEventCompleted:
    """Tests for send_audit_event_completed helper."""

    def test_sends_completed_event(self):
        """send_audit_event_completed sends a ZzzCustomEvent with MCP_TOOL_COMPLETED."""
        mock_audit = MagicMock()
        with patch(
            "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
            return_value=_TENANT_UUID,
        ):
            send_audit_event_completed(mock_audit, "my-tool", "user@example.com")
        event = mock_audit.send.call_args[0][0]
        assert event.common.app_context["event_name"] == MCP_TOOL_COMPLETED
        assert event.common.tenant_id == _TENANT_UUID

    def test_no_op_without_audit_client(self):
        send_audit_event_completed(None, "tool-name")

    def test_disabled_skips_send(self):
        mock_audit = MagicMock()
        with patch(
            "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
            return_value=_TENANT_UUID,
        ):
            send_audit_event_completed(mock_audit, "my-tool", mode=AuditLogMode.DISABLED)
        mock_audit.send.assert_not_called()


class TestSendAuditEventFailed:
    """Tests for send_audit_event_failed helper."""

    def test_sends_failed_event_with_error_type(self):
        """send_audit_event_failed sends MCP_TOOL_FAILED with error_type in payload."""
        mock_audit = MagicMock()
        with patch(
            "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
            return_value=_TENANT_UUID,
        ):
            send_audit_event_failed(mock_audit, "my-tool", "ValueError", "user@example.com")
        event = mock_audit.send.call_args[0][0]
        assert event.common.app_context["event_name"] == MCP_TOOL_FAILED
        assert event.common.tenant_id == _TENANT_UUID

    def test_no_op_without_audit_client(self):
        send_audit_event_failed(None, "tool-name", "RuntimeError")

    def test_disabled_skips_send(self):
        mock_audit = MagicMock()
        with patch(
            "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
            return_value=_TENANT_UUID,
        ):
            send_audit_event_failed(mock_audit, "my-tool", "RuntimeError", mode=AuditLogMode.DISABLED)
        mock_audit.send.assert_not_called()



# ============================================================
# Test: call_mcp_tool audit logging
# ============================================================


class TestCallMcpToolAuditLog:
    """Tests that call_mcp_tool emits audit events for the full tool lifecycle."""

    @pytest.mark.asyncio
    async def test_lob_flow_sends_invoked_and_completed(self, mock_tool):
        """call_mcp_tool sends MCP_TOOL_INVOKED then MCP_TOOL_COMPLETED on success."""
        mock_audit = MagicMock()
        with (
            patch(
                "sap_cloud_sdk.core.auditlog_ng.helper.auditlog_ng.create_client",
                return_value=mock_audit,
            ),
            patch(
                "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
                return_value=_TENANT_UUID,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
                new_callable=AsyncMock,
                return_value=("user-token", "https://agw.example.com"),
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_lob",
                new_callable=AsyncMock,
                return_value="result",
            ),
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")
            await agw_client.call_mcp_tool(
                tool=mock_tool,
                user_token="user-jwt",
                user_id="user@example.com",
            )

        assert mock_audit.send.call_count == 2
        invoked_event = mock_audit.send.call_args_list[0][0][0]
        completed_event = mock_audit.send.call_args_list[1][0][0]
        assert invoked_event.common.app_context["event_name"] == "MCP_TOOL_INVOKED"
        assert invoked_event.common.tenant_id == _TENANT_UUID
        assert invoked_event.common.user_initiator_id == "user@example.com"
        assert completed_event.common.app_context["event_name"] == "MCP_TOOL_COMPLETED"

    @pytest.mark.asyncio
    async def test_customer_flow_no_audit_event(self, mock_tool):
        """call_mcp_tool does not send audit events for customer agents (no tenant_subdomain)."""
        mock_audit = MagicMock()
        with (
            patch(
                "sap_cloud_sdk.core.auditlog_ng.helper.auditlog_ng.create_client",
                return_value=mock_audit,
            ),
            patch(
                "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
                return_value=_TENANT_UUID,
            ),
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
                return_value="result",
            ),
        ):
            mock_creds = MagicMock()
            mock_creds.gateway_url = "https://agw.customer.com"
            mock_load.return_value = mock_creds

            agw_client = create_client()
            await agw_client.call_mcp_tool(
                tool=mock_tool,
                user_token="user-jwt",
            )

        mock_audit.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_lob_flow_sends_invoked_and_failed_on_error(self, mock_tool):
        """call_mcp_tool sends MCP_TOOL_INVOKED then MCP_TOOL_FAILED when tool raises."""
        mock_audit = MagicMock()
        with (
            patch(
                "sap_cloud_sdk.core.auditlog_ng.helper.auditlog_ng.create_client",
                return_value=mock_audit,
            ),
            patch(
                "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
                return_value=_TENANT_UUID,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
                new_callable=AsyncMock,
                return_value=("user-token", "https://agw.example.com"),
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_lob",
                new_callable=AsyncMock,
                side_effect=RuntimeError("invocation error"),
            ),
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")
            with pytest.raises(AgentGatewaySDKError):
                await agw_client.call_mcp_tool(
                    tool=mock_tool,
                    user_token="user-jwt",
                )

        assert mock_audit.send.call_count == 2
        invoked_event = mock_audit.send.call_args_list[0][0][0]
        failed_event = mock_audit.send.call_args_list[1][0][0]
        assert invoked_event.common.app_context["event_name"] == "MCP_TOOL_INVOKED"
        assert failed_event.common.app_context["event_name"] == "MCP_TOOL_FAILED"

    @pytest.mark.asyncio
    async def test_audit_event_uses_tool_name(self, mock_tool):
        """call_mcp_tool stamps tool.name in the invoked audit event payload."""
        mock_audit = MagicMock()
        with (
            patch(
                "sap_cloud_sdk.core.auditlog_ng.helper.auditlog_ng.create_client",
                return_value=mock_audit,
            ),
            patch(
                "sap_cloud_sdk.core.auditlog_ng.helper.get_tenant_id",
                return_value=_TENANT_UUID,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.fetch_user_auth",
                new_callable=AsyncMock,
                return_value=("user-token", "https://agw.example.com"),
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.call_mcp_tool_lob",
                new_callable=AsyncMock,
                return_value="ok",
            ),
        ):
            agw_client = create_client(tenant_subdomain="my-tenant")
            await agw_client.call_mcp_tool(tool=mock_tool, user_token="jwt")

        invoked_event = mock_audit.send.call_args_list[0][0][0]
        assert invoked_event.custom.struct_value.fields["tool"].string_value == "test-tool"
