"""Unit tests for Agent Gateway client."""

import time
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
import pytest

from sap_cloud_sdk.agentgateway import (
    create_client,
    AgentGatewayClient,
    MCPTool,
    AgentGatewaySDKError,
)
from sap_cloud_sdk.agentgateway._models import (
    CustomerCredentials,
    IntegrationDependency,
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

            mock_lob.assert_called_once_with("my-tenant", 60.0)

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

            mock_lob.assert_called_once_with("my-tenant", 60.0)

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
                mock_tool, "my-jwt", "my-tenant", 60.0, param1="value1"
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
            mock_lob.assert_called_once_with(mock_tool, "my-jwt", "my-tenant", 60.0)

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
                mock_tool, "jwt-token", "my-tenant", 60.0, order_id="12345"
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


# ============================================================
# Test: Token cache behavior through the public API
# ============================================================


def _customer_credentials() -> CustomerCredentials:
    """Build a minimal CustomerCredentials fixture for cache-behavior tests."""
    return CustomerCredentials(
        token_service_url="https://ias.example.com/oauth2/token",
        client_id="test-client",
        certificate="cert",
        private_key="key",
        gateway_url="https://agw.example.com",
        integration_dependencies=[
            IntegrationDependency(
                ord_id="sap.test:apiResource:demo:v1",
                global_tenant_id="250695",
            ),
        ],
    )


def _build_streaming_mocks(
    initialize_side_effect=None,
    call_tool_side_effect=None,
    list_tools_side_effect=None,
):
    """Build the chain of mocks needed to drive customer flow MCP calls."""
    http_client = AsyncMock()
    http_client.__aenter__ = AsyncMock(return_value=http_client)
    http_client.__aexit__ = AsyncMock(return_value=None)

    stream_ctx = AsyncMock()
    stream_ctx.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock(), None))
    stream_ctx.__aexit__ = AsyncMock(return_value=None)

    session = AsyncMock()
    if initialize_side_effect is not None:
        session.initialize = AsyncMock(side_effect=initialize_side_effect)
    else:
        init_result = MagicMock()
        init_result.serverInfo.name = "demo-server"
        session.initialize = AsyncMock(return_value=init_result)

    if list_tools_side_effect is not None:
        session.list_tools = AsyncMock(side_effect=list_tools_side_effect)
    else:
        list_result = MagicMock()
        list_result.tools = []
        session.list_tools = AsyncMock(return_value=list_result)

    if call_tool_side_effect is not None:
        session.call_tool = AsyncMock(side_effect=call_tool_side_effect)
    else:
        call_result = MagicMock()
        content = MagicMock()
        content.text = "ok"
        call_result.content = [content]
        session.call_tool = AsyncMock(return_value=call_result)

    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=session)
    session_ctx.__aexit__ = AsyncMock(return_value=None)

    return http_client, stream_ctx, session_ctx


def _make_401() -> httpx.HTTPStatusError:
    """Construct an httpx 401 HTTPStatusError for simulating MCP auth failures."""
    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(401, request=request)
    return httpx.HTTPStatusError("Unauthorized", request=request, response=response)


def _patch_customer_flow(token_request_side_effect):
    """Patch detection/loading + IAS request + MCP transport for customer flow.

    Returns the http/stream/session mocks plus the IAS request mock so callers
    can assert on call counts.
    """
    http_client, stream_ctx, session_ctx = _build_streaming_mocks()

    request_mock = MagicMock(side_effect=token_request_side_effect)

    patches = [
        patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
            return_value="/path/to/credentials",
        ),
        patch(
            "sap_cloud_sdk.agentgateway.agw_client.load_customer_credentials",
            return_value=_customer_credentials(),
        ),
        patch(
            "sap_cloud_sdk.agentgateway._customer._request_token_mtls",
            request_mock,
        ),
        patch("httpx.AsyncClient", return_value=http_client),
        patch(
            "sap_cloud_sdk.agentgateway._customer.streamable_http_client",
            return_value=stream_ctx,
        ),
        patch(
            "sap_cloud_sdk.agentgateway._customer.ClientSession",
            return_value=session_ctx,
        ),
    ]
    return patches, request_mock, session_ctx


class TestTokenCacheBehavior:
    """Cache behavior verified through AgentGatewayClient public API."""

    @pytest.mark.asyncio
    async def test_list_mcp_tools_twice_hits_ias_once(self, mock_tool):
        """Two list_mcp_tools calls share one cached system token."""
        patches, request_mock, _ = _patch_customer_flow(
            token_request_side_effect=lambda *a, **kw: (
                "system-token",
                time.monotonic() + 600,
            )
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            agw_client = create_client()

            await agw_client.list_mcp_tools()
            await agw_client.list_mcp_tools()

            assert request_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_call_mcp_tool_twice_same_user_token_hits_ias_once(self, mock_tool):
        """Two call_mcp_tool calls with same user_token reuse exchanged token."""
        patches, request_mock, _ = _patch_customer_flow(
            token_request_side_effect=lambda *a, **kw: (
                "exchanged-token",
                time.monotonic() + 600,
            )
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            agw_client = create_client()

            await agw_client.call_mcp_tool(tool=mock_tool, user_token="user-jwt-A")
            await agw_client.call_mcp_tool(tool=mock_tool, user_token="user-jwt-A")

            assert request_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_different_user_tokens_isolated(self, mock_tool):
        """Different user_tokens trigger separate exchanges."""
        patches, request_mock, _ = _patch_customer_flow(
            token_request_side_effect=[
                ("tok-A", time.monotonic() + 600),
                ("tok-B", time.monotonic() + 600),
            ]
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            agw_client = create_client()

            await agw_client.call_mcp_tool(tool=mock_tool, user_token="user-jwt-A")
            await agw_client.call_mcp_tool(tool=mock_tool, user_token="user-jwt-B")

            assert request_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_app_tid_isolation(self, mock_tool):
        """Same user_token across different app_tid values stays isolated."""
        patches, request_mock, _ = _patch_customer_flow(
            token_request_side_effect=[
                ("tok-tenant-a", time.monotonic() + 600),
                ("tok-tenant-b", time.monotonic() + 600),
            ]
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            agw_client = create_client()

            await agw_client.call_mcp_tool(
                tool=mock_tool, user_token="user-jwt", app_tid="tenant-a"
            )
            await agw_client.call_mcp_tool(
                tool=mock_tool, user_token="user-jwt", app_tid="tenant-b"
            )

            assert request_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_token_cache_forces_refetch(self, mock_tool):
        """clear_token_cache drops cached tokens, next call refetches."""
        patches, request_mock, _ = _patch_customer_flow(
            token_request_side_effect=lambda *a, **kw: (
                "any-token",
                time.monotonic() + 600,
            )
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            agw_client = create_client()

            await agw_client.call_mcp_tool(tool=mock_tool, user_token="user-jwt")
            agw_client.clear_token_cache()
            await agw_client.call_mcp_tool(tool=mock_tool, user_token="user-jwt")

            assert request_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_401_invalidates_cache_and_retries(self, mock_tool):
        """A 401 from the MCP server drops the cached token and retries once."""
        http_client, stream_ctx, _ = _build_streaming_mocks()

        # First call_tool raises 401, second returns success
        success = MagicMock()
        content = MagicMock()
        content.text = "ok-after-retry"
        success.content = [content]

        session = AsyncMock()
        init_result = MagicMock()
        init_result.serverInfo.name = "demo-server"
        session.initialize = AsyncMock(return_value=init_result)
        session.call_tool = AsyncMock(side_effect=[_make_401(), success])
        session_ctx = AsyncMock()
        session_ctx.__aenter__ = AsyncMock(return_value=session)
        session_ctx.__aexit__ = AsyncMock(return_value=None)

        request_mock = MagicMock(
            side_effect=[
                ("stale-token", time.monotonic() + 600),
                ("fresh-token", time.monotonic() + 600),
            ]
        )

        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value="/path/to/credentials",
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.load_customer_credentials",
                return_value=_customer_credentials(),
            ),
            patch(
                "sap_cloud_sdk.agentgateway._customer._request_token_mtls",
                request_mock,
            ),
            patch("httpx.AsyncClient", return_value=http_client),
            patch(
                "sap_cloud_sdk.agentgateway._customer.streamable_http_client",
                return_value=stream_ctx,
            ),
            patch(
                "sap_cloud_sdk.agentgateway._customer.ClientSession",
                return_value=session_ctx,
            ),
        ):
            agw_client = create_client()

            result = await agw_client.call_mcp_tool(
                tool=mock_tool, user_token="user-jwt"
            )

            assert result == "ok-after-retry"
            # Stale exchange + fresh exchange after invalidation
            assert request_mock.call_count == 2

