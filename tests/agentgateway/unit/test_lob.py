"""Unit tests for LoB agent flow."""

import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from sap_cloud_sdk.agentgateway._fragments import (
    LABEL_KEY,
    FragmentLabel,
    get_ias_fragment_name,
    get_ias_user_fragment_name,
    list_mcp_fragments,
    list_a2a_fragments,
)
from sap_cloud_sdk.agentgateway._lob import (
    _ias_dest_name,
    _fetch_auth_token,
    _ord_id_from_url,
    fetch_system_auth,
    fetch_user_auth,
    get_mcp_tools_lob,
    get_agent_cards_lob,
    _fetch_agent_card,
    call_mcp_tool_lob,
)
from sap_cloud_sdk.agentgateway._models import Agent, AgentCard, MCPTool
from sap_cloud_sdk.agentgateway._token_cache import _GatewayUrlCache, _TokenCache
from sap_cloud_sdk.agentgateway.config import ClientConfig
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError, MCPServerNotFoundError
from sap_cloud_sdk.destination import ConsumptionLevel

# Aliases for use in existing test assertions
_LABEL_KEY = LABEL_KEY
_MCP_LABEL_VALUE = FragmentLabel.MCP.value
_IAS_LABEL_VALUE = FragmentLabel.IAS.value
_IAS_USER_LABEL_VALUE = FragmentLabel.IAS_USER.value
_A2A_LABEL_VALUE = FragmentLabel.A2A.value


# ============================================================
# Test: _ias_dest_name
# ============================================================


class TestIasDestName:
    """Tests for _ias_dest_name function."""

    def test_returns_correct_format(self):
        """Return destination name in correct format."""
        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            result = _ias_dest_name()
            assert result == "sap-managed-runtime-ias-eu10"

    def test_different_landscapes(self):
        """Return correct name for different landscapes."""
        for landscape in ["eu10", "us10", "ap10", "dev"]:
            with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": landscape}):
                result = _ias_dest_name()
                assert result == f"sap-managed-runtime-ias-{landscape}"

    def test_raises_when_env_not_set(self):
        """Raise EnvironmentError when APPFND_CONHOS_LANDSCAPE not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("APPFND_CONHOS_LANDSCAPE", None)

            with pytest.raises(EnvironmentError, match="APPFND_CONHOS_LANDSCAPE"):
                _ias_dest_name()


# ============================================================
# Test: _fetch_auth_token
# ============================================================


class TestFetchAuthToken:
    """Tests for _fetch_auth_token function."""

    def test_fetches_and_decodes_token_and_url(self):
        """Strip Bearer prefix from auth header and return raw JWT with gateway URL."""
        header_value = "Bearer my-raw-jwt-token-123"
        mock_dest = MagicMock()
        mock_dest.auth_tokens = [MagicMock()]
        mock_dest.auth_tokens[0].http_header = {"value": header_value}
        mock_dest.url = "https://agw.example.com/"

        with patch(
            "sap_cloud_sdk.agentgateway._lob.create_destination_client"
        ) as mock_client:
            mock_client.return_value.get_destination.return_value = mock_dest

            result = _fetch_auth_token("dest-name", "tenant-sub")

            assert result == ("my-raw-jwt-token-123", "https://agw.example.com")
            mock_client.return_value.get_destination.assert_called_once_with(
                "dest-name",
                level=ConsumptionLevel.PROVIDER_SUBACCOUNT,
                options=None,
                tenant="tenant-sub",
            )

    def test_strips_trailing_slashes_from_url(self):
        """Strip trailing slashes from gateway URL."""
        header_value = "Bearer token"
        mock_dest = MagicMock()
        mock_dest.auth_tokens = [MagicMock()]
        mock_dest.auth_tokens[0].http_header = {"value": header_value}
        mock_dest.url = "https://agw.example.com/v1/mcp///"

        with patch("sap_cloud_sdk.agentgateway._lob.create_destination_client") as mock_client:
            mock_client.return_value.get_destination.return_value = mock_dest

            result = _fetch_auth_token("dest-name", "tenant-sub")

            assert result == ("token", "https://agw.example.com/v1/mcp")

    def test_raises_when_no_destination(self):
        """Raise MCPServerNotFoundError when destination is None."""
        with patch(
            "sap_cloud_sdk.agentgateway._lob.create_destination_client"
        ) as mock_client:
            mock_client.return_value.get_destination.return_value = None

            with pytest.raises(MCPServerNotFoundError, match="No auth token"):
                _fetch_auth_token("dest-name", "tenant-sub")

    def test_raises_when_no_auth_tokens(self):
        """Raise MCPServerNotFoundError when no auth tokens."""
        mock_dest = MagicMock()
        mock_dest.auth_tokens = []

        with patch(
            "sap_cloud_sdk.agentgateway._lob.create_destination_client"
        ) as mock_client:
            mock_client.return_value.get_destination.return_value = mock_dest

            with pytest.raises(MCPServerNotFoundError, match="No auth token"):
                _fetch_auth_token("dest-name", "tenant-sub")

    def test_raises_when_empty_token_value(self):
        """Raise MCPServerNotFoundError when http_header value is empty."""
        mock_dest = MagicMock()
        mock_dest.auth_tokens = [MagicMock()]
        mock_dest.auth_tokens[0].http_header = {"value": ""}

        with patch(
            "sap_cloud_sdk.agentgateway._lob.create_destination_client"
        ) as mock_client:
            mock_client.return_value.get_destination.return_value = mock_dest

            with pytest.raises(MCPServerNotFoundError, match="Empty auth header"):
                _fetch_auth_token("dest-name", "tenant-sub")

    def test_passes_options_to_destination(self):
        """Pass consumption options to get_destination."""
        mock_dest = MagicMock()
        mock_dest.auth_tokens = [MagicMock()]
        mock_dest.auth_tokens[0].http_header = {"value": "Bearer token"}
        mock_dest.url = "https://agw.example.com"
        mock_options = MagicMock()

        with patch(
            "sap_cloud_sdk.agentgateway._lob.create_destination_client"
        ) as mock_client:
            mock_client.return_value.get_destination.return_value = mock_dest

            _fetch_auth_token("dest-name", "tenant-sub", options=mock_options)

            mock_client.return_value.get_destination.assert_called_once_with(
                "dest-name",
                level=ConsumptionLevel.PROVIDER_SUBACCOUNT,
                options=mock_options,
                tenant="tenant-sub",
            )


# ============================================================
# Test: list_mcp_fragments
# ============================================================


class TestListMcpFragments:
    """Tests for list_mcp_fragments function."""

    def test_returns_all_mcp_fragments(self):
        """Return all fragments with agw.mcp.server label."""
        fragment1 = MagicMock()
        fragment1.name = "mcp-server-a"

        fragment2 = MagicMock()
        fragment2.name = "mcp-server-b"

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client"
        ) as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = [
                fragment1,
                fragment2,
            ]

            result = list_mcp_fragments("tenant-sub")

            assert len(result) == 2
            assert fragment1 in result
            assert fragment2 in result

    def test_uses_correct_filter_labels(self):
        """Use correct label filter for MCP fragments."""
        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client"
        ) as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = []

            list_mcp_fragments("tenant-sub")

            mock_client.assert_called_once_with(instance="default")
            call_args = mock_client.return_value.list_instance_fragments.call_args
            filter_opt = call_args.kwargs.get("filter")
            assert filter_opt is not None
            assert len(filter_opt.filter_labels) == 1
            assert filter_opt.filter_labels[0].key == _LABEL_KEY
            assert filter_opt.filter_labels[0].values == [_MCP_LABEL_VALUE]


# ============================================================
# Test: get_ias_fragment_name
# ============================================================


class TestGetIasFragmentName:
    """Tests for get_ias_fragment_name function."""

    def test_returns_fragment_name(self):
        """Return name of first IAS fragment found."""
        fragment = MagicMock()
        fragment.name = "sap-managed-runtime-agw-subscriber-ias-abc123"

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client"
        ) as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = [fragment]

            result = get_ias_fragment_name("tenant-sub")

            assert result == "sap-managed-runtime-agw-subscriber-ias-abc123"

    def test_uses_correct_filter_labels(self):
        """Use correct label filter for IAS fragments."""
        fragment = MagicMock()
        fragment.name = "ias-fragment"

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client"
        ) as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = [fragment]

            get_ias_fragment_name("tenant-sub")

            call_args = mock_client.return_value.list_instance_fragments.call_args
            filter_opt = call_args.kwargs.get("filter")
            assert filter_opt is not None
            assert len(filter_opt.filter_labels) == 1
            assert filter_opt.filter_labels[0].key == _LABEL_KEY
            assert filter_opt.filter_labels[0].values == [_IAS_LABEL_VALUE]

    def test_raises_when_no_fragment_found(self):
        """Raise MCPServerNotFoundError when no IAS fragment exists."""
        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client"
        ) as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = []

            with pytest.raises(MCPServerNotFoundError, match="No IAS fragment found"):
                get_ias_fragment_name("tenant-sub")


# ============================================================
# Test: get_ias_user_fragment_name
# ============================================================


class TestGetIasUserFragmentName:
    """Tests for get_ias_user_fragment_name function."""

    def test_returns_fragment_name(self):
        """Return name of first IAS user fragment found."""
        fragment = MagicMock()
        fragment.name = "sap-managed-runtime-agw-subscriber-ias-user-abc123"

        with patch("sap_cloud_sdk.agentgateway._fragments.create_fragment_client") as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = [fragment]

            result = get_ias_user_fragment_name("tenant-sub")

            assert result == "sap-managed-runtime-agw-subscriber-ias-user-abc123"

    def test_uses_correct_filter_labels(self):
        """Use correct label filter for IAS user fragments."""
        fragment = MagicMock()
        fragment.name = "ias-user-fragment"

        with patch("sap_cloud_sdk.agentgateway._fragments.create_fragment_client") as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = [fragment]

            get_ias_user_fragment_name("tenant-sub")

            call_args = mock_client.return_value.list_instance_fragments.call_args
            filter_opt = call_args.kwargs.get("filter")
            assert filter_opt is not None
            assert len(filter_opt.filter_labels) == 1
            assert filter_opt.filter_labels[0].key == _LABEL_KEY
            assert filter_opt.filter_labels[0].values == [_IAS_USER_LABEL_VALUE]

    def test_raises_when_no_fragment_found(self):
        """Raise MCPServerNotFoundError when no IAS user fragment exists."""
        with patch("sap_cloud_sdk.agentgateway._fragments.create_fragment_client") as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = []

            with pytest.raises(MCPServerNotFoundError, match="No IAS user fragment found"):
                get_ias_user_fragment_name("tenant-sub")


# ============================================================
# Test: fetch_system_auth
# ============================================================


class TestFetchSystemAuth:
    """Tests for fetch_system_auth async function."""

    @pytest.mark.asyncio
    async def test_fetches_system_auth(self):
        """Fetch system auth using IAS fragment and return tuple (token, url)."""
        raw_token = "system-jwt-token-xyz"
        gateway_url = "https://agw.example.com"

        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            with (
                patch(
                    "sap_cloud_sdk.agentgateway._lob.get_ias_fragment_name"
                ) as mock_ias,
                patch(
                    "sap_cloud_sdk.agentgateway._lob._fetch_auth_token"
                ) as mock_fetch,
            ):
                mock_ias.return_value = "sap-managed-runtime-agw-subscriber-ias-abc"
                mock_fetch.return_value = (raw_token, gateway_url)

                result = await fetch_system_auth("tenant-sub")

                assert result == (raw_token, gateway_url)
                mock_ias.assert_called_once_with("tenant-sub")
                mock_fetch.assert_called_once()
                call_args = mock_fetch.call_args
                assert call_args[0][0] == "sap-managed-runtime-ias-eu10"
                assert call_args[0][1] == "tenant-sub"
                assert (
                    call_args[0][2].fragment_name
                    == "sap-managed-runtime-agw-subscriber-ias-abc"
                )
                assert call_args[0][2].fragment_level == ConsumptionLevel.INSTANCE

    @pytest.mark.asyncio
    async def test_reuses_cached_system_auth(self):
        """Reuse tenant-scoped system auth until it expires."""
        token_cache = _TokenCache(ClientConfig())
        gateway_url_cache = _GatewayUrlCache()

        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            with (
                patch(
                    "sap_cloud_sdk.agentgateway._lob.get_ias_fragment_name",
                    return_value="sap-managed-runtime-agw-subscriber-ias-abc",
                ),
                patch(
                    "sap_cloud_sdk.agentgateway._lob._fetch_auth_token",
                    return_value=("system-token", "https://agw.example.com"),
                ) as mock_fetch,
            ):
                first = await fetch_system_auth(
                    "tenant-sub",
                    token_cache=token_cache,
                    gateway_url_cache=gateway_url_cache,
                )
                second = await fetch_system_auth(
                    "tenant-sub",
                    token_cache=token_cache,
                    gateway_url_cache=gateway_url_cache,
                )

        assert first == ("system-token", "https://agw.example.com")
        assert second == ("system-token", "https://agw.example.com")
        mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_only_token_cache_provided(self):
        """Raise ValueError when token_cache given without gateway_url_cache."""
        with pytest.raises(ValueError, match="both be provided or both be None"):
            await fetch_system_auth("tenant-sub", token_cache=_TokenCache(ClientConfig()))

    @pytest.mark.asyncio
    async def test_raises_when_only_gateway_url_cache_provided(self):
        """Raise ValueError when gateway_url_cache given without token_cache."""
        with pytest.raises(ValueError, match="both be provided or both be None"):
            await fetch_system_auth("tenant-sub", gateway_url_cache=_GatewayUrlCache())


# ============================================================
# Test: fetch_user_auth
# ============================================================


class TestFetchUserAuth:
    """Tests for fetch_user_auth async function."""

    @pytest.mark.asyncio
    async def test_fetches_user_auth_with_ias_user_fragment(self):
        """Fetch user auth using IAS user fragment and user_token, return tuple."""
        raw_token = "exchanged-user-jwt-token"
        gateway_url = "https://agw.example.com"

        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            with (
                patch("sap_cloud_sdk.agentgateway._lob.get_ias_user_fragment_name") as mock_ias_user,
                patch("sap_cloud_sdk.agentgateway._lob._fetch_auth_token") as mock_fetch,
            ):
                mock_ias_user.return_value = "sap-managed-runtime-agw-subscriber-ias-user-abc"
                mock_fetch.return_value = (raw_token, gateway_url)

                result = await fetch_user_auth("user-jwt", "tenant-sub")

                assert result == (raw_token, gateway_url)
                mock_ias_user.assert_called_once_with("tenant-sub")
                mock_fetch.assert_called_once()
                call_args = mock_fetch.call_args
                assert call_args[0][0] == "sap-managed-runtime-ias-eu10"
                assert call_args[0][1] == "tenant-sub"
                options = call_args[0][2]
                assert options.user_token == "user-jwt"
                assert options.fragment_name == "sap-managed-runtime-agw-subscriber-ias-user-abc"
                assert options.fragment_level == ConsumptionLevel.INSTANCE

    @pytest.mark.asyncio
    async def test_reuses_cached_user_auth(self):
        """Reuse tenant-scoped user auth until it expires."""
        token_cache = _TokenCache(ClientConfig())
        gateway_url_cache = _GatewayUrlCache()

        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            with (
                patch(
                    "sap_cloud_sdk.agentgateway._lob.get_ias_user_fragment_name",
                    return_value="sap-managed-runtime-agw-subscriber-ias-user-abc",
                ),
                patch(
                    "sap_cloud_sdk.agentgateway._lob._fetch_auth_token",
                    return_value=("user-token", "https://agw.example.com"),
                ) as mock_fetch,
            ):
                first = await fetch_user_auth(
                    "user-jwt",
                    "tenant-sub",
                    token_cache=token_cache,
                    gateway_url_cache=gateway_url_cache,
                )
                second = await fetch_user_auth(
                    "user-jwt",
                    "tenant-sub",
                    token_cache=token_cache,
                    gateway_url_cache=gateway_url_cache,
                )

        assert first == ("user-token", "https://agw.example.com")
        assert second == ("user-token", "https://agw.example.com")
        mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_only_token_cache_provided(self):
        """Raise ValueError when token_cache given without gateway_url_cache."""
        with pytest.raises(ValueError, match="both be provided or both be None"):
            await fetch_user_auth("user-jwt", "tenant-sub", token_cache=_TokenCache(ClientConfig()))

    @pytest.mark.asyncio
    async def test_raises_when_only_gateway_url_cache_provided(self):
        """Raise ValueError when gateway_url_cache given without token_cache."""
        with pytest.raises(ValueError, match="both be provided or both be None"):
            await fetch_user_auth("user-jwt", "tenant-sub", gateway_url_cache=_GatewayUrlCache())


# ============================================================
# Test: get_mcp_tools_lob
# ============================================================


class TestGetMcpToolsLob:
    """Tests for get_mcp_tools_lob async function."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_fragments(self):
        """Return empty list when no fragments found."""
        with patch("sap_cloud_sdk.agentgateway._lob.list_mcp_fragments") as mock_list:
            mock_list.return_value = []

            result = await get_mcp_tools_lob("tenant-sub", "system-token", 60.0)

            assert result == []

    @pytest.mark.asyncio
    async def test_skips_fragments_without_url(self):
        """Skip fragments that don't have URL property."""
        fragment = MagicMock()
        fragment.name = "mcp-server-a"
        fragment.properties = {}  # No URL

        with patch("sap_cloud_sdk.agentgateway._lob.list_mcp_fragments") as mock_list:
            mock_list.return_value = [fragment]

            result = await get_mcp_tools_lob("tenant-sub", "system-token", 60.0)

            assert result == []

    @pytest.mark.asyncio
    async def test_uses_pre_fetched_system_token(self):
        """Use the pre-fetched system token for MCP server calls."""
        fragment = MagicMock()
        fragment.name = "mcp-server-a"
        fragment.properties = {"URL": "https://example.com/mcp"}

        mock_tool = MCPTool(
            name="test-tool",
            server_name="test-server",
            description="Test",
            input_schema={},
            url="https://example.com/mcp",
            fragment_name="mcp-server-a",
        )

        with (
            patch("sap_cloud_sdk.agentgateway._lob.list_mcp_fragments") as mock_list,
            patch(
                "sap_cloud_sdk.agentgateway._lob.list_server_tools",
                new_callable=AsyncMock,
            ) as mock_tools,
        ):
            mock_list.return_value = [fragment]
            mock_tools.return_value = [mock_tool]

            await get_mcp_tools_lob("tenant-sub", "pre-fetched-token", 60.0)

            # Verify list_server_tools called with the pre-fetched token
            mock_tools.assert_called_once_with(
                "https://example.com/mcp", "pre-fetched-token", "mcp-server-a", 60.0
            )

    @pytest.mark.asyncio
    async def test_handles_exception_for_single_fragment(self):
        """Continue processing other fragments when one fails."""
        fragment1 = MagicMock()
        fragment1.name = "mcp-server1"
        fragment1.properties = {"URL": "https://example1.com/mcp"}

        fragment2 = MagicMock()
        fragment2.name = "mcp-server2"
        fragment2.properties = {"URL": "https://example2.com/mcp"}

        mock_tool = MCPTool(
            name="tool2",
            server_name="server2",
            description="Test",
            input_schema={},
            url="https://example2.com/mcp",
            fragment_name="mcp-server2",
        )

        call_count = 0

        async def mock_list_tools_fn(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Server connection failed")
            return [mock_tool]

        with (
            patch("sap_cloud_sdk.agentgateway._lob.list_mcp_fragments") as mock_list,
            patch(
                "sap_cloud_sdk.agentgateway._lob.list_server_tools",
                side_effect=mock_list_tools_fn,
            ),
        ):
            mock_list.return_value = [fragment1, fragment2]

            result = await get_mcp_tools_lob("tenant-sub", "system-token", 60.0)

            # Should still get tools from second fragment
            assert len(result) == 1
            assert result[0].name == "tool2"


# ============================================================
# Test: call_mcp_tool_lob
# ============================================================


class TestCallMcpToolLob:
    """Tests for call_mcp_tool_lob async function."""

    @pytest.mark.asyncio
    async def test_calls_tool_with_pre_fetched_token(self):
        """Call tool using pre-fetched user auth token."""
        tool = MCPTool(
            name="test-tool",
            server_name="test-server",
            description="Test tool",
            input_schema={},
            url="https://example.com/mcp",
            fragment_name="test-fragment",
        )

        mock_result = MagicMock()
        mock_result.content = [MagicMock()]
        mock_result.content[0].text = "Tool result"

        with (
            patch("sap_cloud_sdk.agentgateway._lob.httpx.AsyncClient") as mock_http,
            patch(
                "sap_cloud_sdk.agentgateway._lob.streamable_http_client"
            ) as mock_stream,
            patch("sap_cloud_sdk.agentgateway._lob.ClientSession") as mock_session,
        ):
            # Setup async context managers
            mock_http_instance = AsyncMock()
            mock_http.return_value.__aenter__.return_value = mock_http_instance

            mock_stream.return_value.__aenter__.return_value = (
                AsyncMock(),
                AsyncMock(),
                None,
            )

            mock_session_instance = AsyncMock()
            mock_session_instance.initialize = AsyncMock()
            mock_session_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            result = await call_mcp_tool_lob(
                tool, "user-auth-token", 60.0, param1="value1"
            )

            assert result == "Tool result"
            mock_session_instance.call_tool.assert_called_once_with(
                "test-tool", {"param1": "value1"}
            )

            # Verify the Authorization header uses Bearer + raw token
            mock_http.assert_called_once()
            call_kwargs = mock_http.call_args.kwargs
            assert call_kwargs["headers"]["Authorization"] == "Bearer user-auth-token"

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_no_content(self):
        """Return empty string when tool returns no content."""
        tool = MCPTool(
            name="test-tool",
            server_name="test-server",
            description="Test tool",
            input_schema={},
            url="https://example.com/mcp",
            fragment_name="test-fragment",
        )

        mock_result = MagicMock()
        mock_result.content = []

        with (
            patch("sap_cloud_sdk.agentgateway._lob.httpx.AsyncClient") as mock_http,
            patch(
                "sap_cloud_sdk.agentgateway._lob.streamable_http_client"
            ) as mock_stream,
            patch("sap_cloud_sdk.agentgateway._lob.ClientSession") as mock_session,
        ):
            mock_http_instance = AsyncMock()
            mock_http.return_value.__aenter__.return_value = mock_http_instance

            mock_stream.return_value.__aenter__.return_value = (
                AsyncMock(),
                AsyncMock(),
                None,
            )

            mock_session_instance = AsyncMock()
            mock_session_instance.initialize = AsyncMock()
            mock_session_instance.call_tool = AsyncMock(return_value=mock_result)
            mock_session.return_value.__aenter__.return_value = mock_session_instance

            result = await call_mcp_tool_lob(tool, "user-auth-token", 60.0)

            assert result == ""


# ============================================================
# Test: list_a2a_fragments
# ============================================================


# ============================================================
# Test: _ord_id_from_url
# ============================================================


class TestOrdIdFromUrl:
    """Tests for _ord_id_from_url helper."""

    def test_extracts_ord_id_from_standard_url(self):
        """Return the second-to-last path segment as ord_id."""
        assert _ord_id_from_url(
            "https://agw.example.com/v1/a2a/sap.s4:agent:v1/tenant-abc"
        ) == "sap.s4:agent:v1"

    def test_strips_trailing_slash(self):
        """Handle trailing slash on URL."""
        assert _ord_id_from_url(
            "https://agw.example.com/v1/a2a/ord-1/gt-1/"
        ) == "ord-1"

    def test_returns_empty_for_single_segment(self):
        """Return empty string when URL has only one path segment."""
        assert _ord_id_from_url("https://agw.example.com/only-one") == ""

    def test_returns_empty_for_bare_host(self):
        """Return empty string for bare host URL with no path."""
        assert _ord_id_from_url("https://agw.example.com") == ""


class TestListA2aFragments:
    """Tests for list_a2a_fragments function."""

    def test_lists_fragments_with_a2a_label(self):
        """Return fragments filtered by agw.a2a label."""
        mock_fragment = MagicMock()
        mock_fragment.name = "a2a-fragment"

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client"
        ) as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = [mock_fragment]
            result = list_a2a_fragments("tenant-sub")

        assert result == [mock_fragment]
        call_kwargs = mock_client.return_value.list_instance_fragments.call_args
        filter_obj = call_kwargs[1]["filter"]
        assert filter_obj.filter_labels[0].key == _LABEL_KEY
        assert _A2A_LABEL_VALUE in filter_obj.filter_labels[0].values

    def test_returns_empty_list_when_no_fragments(self):
        """Return empty list when no A2A fragments exist."""
        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client"
        ) as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = []
            result = list_a2a_fragments("tenant-sub")

        assert result == []


# ============================================================
# Test: _fetch_agent_card
# ============================================================


class TestFetchAgentCard:
    """Tests for _fetch_agent_card async function."""

    @pytest.mark.asyncio
    async def test_fetches_agent_card_successfully(self):
        """Fetch and parse agent card JSON from well-known endpoint."""
        card_payload = {"name": "TestAgent", "version": "1.0", "capabilities": {}}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = card_payload

        with patch("sap_cloud_sdk.agentgateway._lob.httpx.AsyncClient") as mock_http:
            mock_http_instance = AsyncMock()
            mock_http_instance.get = AsyncMock(return_value=mock_response)
            mock_http.return_value.__aenter__.return_value = mock_http_instance

            result = await _fetch_agent_card(
                "https://agw.example.com/v1/a2a/sap.s4:apiAccess:agent:v1/tenant-123",
                "auth-token",
                60.0,
            )

        assert isinstance(result, AgentCard)
        assert result.raw == card_payload
        mock_http_instance.get.assert_called_once_with(
            "https://agw.example.com/v1/a2a/sap.s4:apiAccess:agent:v1/tenant-123/.well-known/agent-card.json"
        )

    @pytest.mark.asyncio
    async def test_strips_trailing_slash_from_fragment_url(self):
        """Strip trailing slash from fragment URL before appending well-known path."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch("sap_cloud_sdk.agentgateway._lob.httpx.AsyncClient") as mock_http:
            mock_http_instance = AsyncMock()
            mock_http_instance.get = AsyncMock(return_value=mock_response)
            mock_http.return_value.__aenter__.return_value = mock_http_instance

            await _fetch_agent_card("https://agw.example.com/base/", "token", 60.0)

        mock_http_instance.get.assert_called_once_with(
            "https://agw.example.com/base/.well-known/agent-card.json"
        )

    @pytest.mark.asyncio
    async def test_raises_on_non_200_status(self):
        """Raise AgentGatewaySDKError when response status is not 200."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        with patch("sap_cloud_sdk.agentgateway._lob.httpx.AsyncClient") as mock_http:
            mock_http_instance = AsyncMock()
            mock_http_instance.get = AsyncMock(return_value=mock_response)
            mock_http.return_value.__aenter__.return_value = mock_http_instance

            with pytest.raises(AgentGatewaySDKError, match="404"):
                await _fetch_agent_card("https://agw.example.com/base", "auth-token", 60.0)

    @pytest.mark.asyncio
    async def test_raises_on_request_error(self):
        """Raise AgentGatewaySDKError when HTTP request fails."""
        import httpx

        with patch("sap_cloud_sdk.agentgateway._lob.httpx.AsyncClient") as mock_http:
            mock_http_instance = AsyncMock()
            mock_http_instance.get = AsyncMock(
                side_effect=httpx.RequestError("connection refused")
            )
            mock_http.return_value.__aenter__.return_value = mock_http_instance

            with pytest.raises(AgentGatewaySDKError, match="Agent card request failed"):
                await _fetch_agent_card("https://agw.example.com/base", "auth-token", 60.0)


# ============================================================
# Test: get_agent_cards_lob
# ============================================================


class TestGetAgentCardsLob:
    """Tests for get_agent_cards_lob async function."""

    def _make_fragment(self, name: str, url: str) -> MagicMock:
        fragment = MagicMock()
        fragment.name = name
        fragment.properties = {"URL": url}
        return fragment

    @pytest.mark.asyncio
    async def test_returns_agents_for_all_fragments(self):
        """Return one Agent per A2A fragment with fetched card."""
        card_payload = {"name": "MyAgent"}
        fragment = self._make_fragment(
            "frag-1", "https://agw.example.com/v1/a2a/sap.s4:agent:v1/tenant-abc"
        )

        with (
            patch(
                "sap_cloud_sdk.agentgateway._lob.list_a2a_fragments",
                return_value=[fragment],
            ),
            patch(
                "sap_cloud_sdk.agentgateway._lob._fetch_agent_card",
                new_callable=AsyncMock,
                return_value=AgentCard(raw=card_payload),
            ),
        ):
            result = await get_agent_cards_lob(
                "tenant-sub", "system-token", 60.0
            )

        assert len(result) == 1
        assert isinstance(result[0], Agent)
        assert result[0].ord_id == "sap.s4:agent:v1"
        assert result[0].agent_card.raw == card_payload

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_fragments(self):
        """Return empty list when no A2A fragments exist."""
        with patch(
            "sap_cloud_sdk.agentgateway._lob.list_a2a_fragments",
            return_value=[],
        ):
            result = await get_agent_cards_lob("tenant-sub", "system-token", 60.0)

        assert result == []

    @pytest.mark.asyncio
    async def test_filters_by_agent_names(self):
        """Fetch all cards then keep only those whose agent card name matches."""
        frag_1 = self._make_fragment("frag-1", "https://agw.example.com/v1/a2a/ord-1/t1")
        frag_2 = self._make_fragment("frag-2", "https://agw.example.com/v1/a2a/ord-2/t2")

        async def _cards_by_ord(fragment_url, token, timeout):
            if "ord-1" in fragment_url:
                return AgentCard(raw={"name": "Billing Agent"})
            return AgentCard(raw={"name": "Other Agent"})

        with (
            patch(
                "sap_cloud_sdk.agentgateway._lob.list_a2a_fragments",
                return_value=[frag_1, frag_2],
            ),
            patch(
                "sap_cloud_sdk.agentgateway._lob._fetch_agent_card",
                side_effect=_cards_by_ord,
            ),
        ):
            result = await get_agent_cards_lob(
                "tenant-sub", "token", 60.0, agent_names=["Billing Agent"]
            )

        assert len(result) == 1
        assert result[0].ord_id == "ord-1"
        assert result[0].agent_card.raw["name"] == "Billing Agent"

    @pytest.mark.asyncio
    async def test_filters_by_ord_ids(self):
        """Only include fragments whose ordId (from URL) is in the ord_ids filter."""
        frag_1 = self._make_fragment("frag-1", "https://agw.example.com/v1/a2a/ord-1/t1")
        frag_2 = self._make_fragment("frag-2", "https://agw.example.com/v1/a2a/ord-2/t2")

        with (
            patch(
                "sap_cloud_sdk.agentgateway._lob.list_a2a_fragments",
                return_value=[frag_1, frag_2],
            ),
            patch(
                "sap_cloud_sdk.agentgateway._lob._fetch_agent_card",
                new_callable=AsyncMock,
                return_value=AgentCard(raw={}),
            ) as mock_fetch,
        ):
            result = await get_agent_cards_lob(
                "tenant-sub", "token", 60.0, ord_ids=["ord-2"]
            )

        assert len(result) == 1
        assert result[0].ord_id == "ord-2"
        assert mock_fetch.call_count == 1

    @pytest.mark.asyncio
    async def test_skips_fragment_with_unparseable_ord_id(self):
        """Skip fragment whose URL has fewer than two path segments (no ordId)."""
        fragment = MagicMock()
        fragment.name = "frag-bad-url"
        fragment.properties = {"URL": "https://agw.example.com"}

        with patch(
            "sap_cloud_sdk.agentgateway._lob.list_a2a_fragments",
            return_value=[fragment],
        ):
            result = await get_agent_cards_lob("tenant-sub", "token", 60.0)

        assert result == []

    @pytest.mark.asyncio
    async def test_skips_fragment_missing_url(self):
        """Skip fragment that has no URL property."""
        fragment = MagicMock()
        fragment.name = "frag-no-url"
        fragment.properties = {}

        with patch(
            "sap_cloud_sdk.agentgateway._lob.list_a2a_fragments",
            return_value=[fragment],
        ):
            result = await get_agent_cards_lob("tenant-sub", "token", 60.0)

        assert result == []

    @pytest.mark.asyncio
    async def test_skips_fragment_on_fetch_error(self):
        """Skip fragment when agent card fetch fails, continue with others."""
        frag_ok = self._make_fragment(
            "frag-ok", "https://agw.example.com/v1/a2a/ord-ok/t-ok"
        )
        frag_err = self._make_fragment(
            "frag-err", "https://agw.example.com/v1/a2a/ord-err/t-err"
        )

        async def _selective_fetch(fragment_url, token, timeout):
            if "ord-err" in fragment_url:
                raise RuntimeError("server unreachable")
            return AgentCard(raw={"name": "OK"})

        with (
            patch(
                "sap_cloud_sdk.agentgateway._lob.list_a2a_fragments",
                return_value=[frag_ok, frag_err],
            ),
            patch(
                "sap_cloud_sdk.agentgateway._lob._fetch_agent_card",
                side_effect=_selective_fetch,
            ),
        ):
            result = await get_agent_cards_lob("tenant-sub", "token", 60.0)

        assert len(result) == 1
        assert result[0].ord_id == "ord-ok"
