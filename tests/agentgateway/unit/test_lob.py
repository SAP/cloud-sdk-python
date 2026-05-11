"""Unit tests for LoB agent flow."""

import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from sap_cloud_sdk.agentgateway._lob import (
    _ias_dest_name,
    _fetch_auth_token,
    list_mcp_fragments,
    get_ias_fragment_name,
    get_system_auth,
    get_user_auth,
    get_mcp_tools_lob,
    call_mcp_tool_lob,
    _LABEL_KEY,
    _MCP_LABEL_VALUE,
    _IAS_LABEL_VALUE,
)
from sap_cloud_sdk.agentgateway._models import MCPTool
from sap_cloud_sdk.agentgateway.exceptions import MCPServerNotFoundError
from sap_cloud_sdk.destination import ConsumptionLevel


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

    def test_fetches_token_successfully(self):
        """Fetch auth token from destination service."""
        mock_dest = MagicMock()
        mock_dest.auth_tokens = [MagicMock()]
        mock_dest.auth_tokens[0].http_header = {"value": "Bearer test-token"}

        with patch(
            "sap_cloud_sdk.agentgateway._lob.create_destination_client"
        ) as mock_client:
            mock_client.return_value.get_destination.return_value = mock_dest

            result = _fetch_auth_token("dest-name", "tenant-sub")

            assert result == "Bearer test-token"
            mock_client.return_value.get_destination.assert_called_once_with(
                "dest-name",
                level=ConsumptionLevel.PROVIDER_SUBACCOUNT,
                options=None,
                tenant="tenant-sub",
            )

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

    def test_raises_when_empty_auth_header(self):
        """Raise MCPServerNotFoundError when auth header is empty."""
        mock_dest = MagicMock()
        mock_dest.auth_tokens = [MagicMock()]
        mock_dest.auth_tokens[0].http_header = {"value": ""}

        with patch(
            "sap_cloud_sdk.agentgateway._lob.create_destination_client"
        ) as mock_client:
            mock_client.return_value.get_destination.return_value = mock_dest

            with pytest.raises(MCPServerNotFoundError, match="Empty Authorization"):
                _fetch_auth_token("dest-name", "tenant-sub")

    def test_passes_options_to_destination(self):
        """Pass consumption options to get_destination."""
        mock_dest = MagicMock()
        mock_dest.auth_tokens = [MagicMock()]
        mock_dest.auth_tokens[0].http_header = {"value": "Bearer token"}
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
            "sap_cloud_sdk.agentgateway._lob.create_fragment_client"
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
            "sap_cloud_sdk.agentgateway._lob.create_fragment_client"
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
            "sap_cloud_sdk.agentgateway._lob.create_fragment_client"
        ) as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = [fragment]

            result = get_ias_fragment_name("tenant-sub")

            assert result == "sap-managed-runtime-agw-subscriber-ias-abc123"

    def test_uses_correct_filter_labels(self):
        """Use correct label filter for IAS fragments."""
        fragment = MagicMock()
        fragment.name = "ias-fragment"

        with patch(
            "sap_cloud_sdk.agentgateway._lob.create_fragment_client"
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
            "sap_cloud_sdk.agentgateway._lob.create_fragment_client"
        ) as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = []

            with pytest.raises(MCPServerNotFoundError, match="No IAS fragment found"):
                get_ias_fragment_name("tenant-sub")


# ============================================================
# Test: get_system_auth
# ============================================================


class TestGetSystemAuth:
    """Tests for get_system_auth async function."""

    @pytest.mark.asyncio
    async def test_fetches_system_auth(self):
        """Fetch system auth using IAS fragment looked up by label."""
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
                mock_fetch.return_value = "Bearer system-token"

                result = await get_system_auth("tenant-sub")

                assert result == "Bearer system-token"
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


# ============================================================
# Test: get_user_auth
# ============================================================


class TestGetUserAuth:
    """Tests for get_user_auth async function."""

    @pytest.mark.asyncio
    async def test_fetches_user_auth_with_token_exchange(self):
        """Fetch user auth with token exchange."""
        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            with patch(
                "sap_cloud_sdk.agentgateway._lob._fetch_auth_token"
            ) as mock_fetch:
                mock_fetch.return_value = "Bearer user-token"

                result = await get_user_auth("mcp-fragment", "user-jwt", "tenant-sub")

                assert result == "Bearer user-token"
                mock_fetch.assert_called_once()
                call_args = mock_fetch.call_args
                assert call_args[0][0] == "sap-managed-runtime-ias-eu10"
                assert call_args[0][1] == "tenant-sub"
                options = call_args[0][2]
                assert options.user_token == "user-jwt"
                assert options.fragment_name == "mcp-fragment"
                assert options.fragment_level == ConsumptionLevel.INSTANCE


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

            result = await get_mcp_tools_lob("tenant-sub")

            assert result == []

    @pytest.mark.asyncio
    async def test_skips_fragments_without_url(self):
        """Skip fragments that don't have URL property."""
        fragment = MagicMock()
        fragment.name = "mcp-server-a"
        fragment.properties = {}  # No URL

        with patch("sap_cloud_sdk.agentgateway._lob.list_mcp_fragments") as mock_list:
            mock_list.return_value = [fragment]

            result = await get_mcp_tools_lob("tenant-sub")

            assert result == []

    @pytest.mark.asyncio
    async def test_uses_fragment_name_directly(self):
        """Use fragment name as-is (no -technical stripping)."""
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
                "sap_cloud_sdk.agentgateway._lob.get_system_auth",
                new_callable=AsyncMock,
            ) as mock_auth,
            patch(
                "sap_cloud_sdk.agentgateway._lob.list_server_tools",
                new_callable=AsyncMock,
            ) as mock_tools,
        ):
            mock_list.return_value = [fragment]
            mock_auth.return_value = "Bearer token"
            mock_tools.return_value = [mock_tool]

            await get_mcp_tools_lob("tenant-sub")

            # Verify get_system_auth called with just tenant_subdomain
            mock_auth.assert_called_once_with("tenant-sub")
            # Verify list_server_tools called with the unchanged fragment name
            mock_tools.assert_called_once()
            call_args = mock_tools.call_args[0]
            assert call_args[2] == "mcp-server-a"

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

        with (
            patch("sap_cloud_sdk.agentgateway._lob.list_mcp_fragments") as mock_list,
            patch(
                "sap_cloud_sdk.agentgateway._lob.get_system_auth",
                new_callable=AsyncMock,
            ) as mock_auth,
            patch(
                "sap_cloud_sdk.agentgateway._lob.list_server_tools",
                new_callable=AsyncMock,
            ) as mock_tools,
        ):
            mock_list.return_value = [fragment1, fragment2]

            # First fragment fails, second succeeds
            mock_auth.side_effect = [Exception("Auth failed"), "Bearer token"]
            mock_tools.return_value = [mock_tool]

            result = await get_mcp_tools_lob("tenant-sub")

            # Should still get tools from second fragment
            assert len(result) == 1
            assert result[0].name == "tool2"


# ============================================================
# Test: call_mcp_tool_lob
# ============================================================


class TestCallMcpToolLob:
    """Tests for call_mcp_tool_lob async function."""

    @pytest.mark.asyncio
    async def test_calls_tool_with_user_auth(self):
        """Call tool using user authentication."""
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
            patch(
                "sap_cloud_sdk.agentgateway._lob.get_user_auth", new_callable=AsyncMock
            ) as mock_auth,
            patch("sap_cloud_sdk.agentgateway._lob.httpx.AsyncClient") as mock_http,
            patch(
                "sap_cloud_sdk.agentgateway._lob.streamable_http_client"
            ) as mock_stream,
            patch("sap_cloud_sdk.agentgateway._lob.ClientSession") as mock_session,
        ):
            mock_auth.return_value = "Bearer user-token"

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
                tool, "user-jwt", "tenant-sub", param1="value1"
            )

            assert result == "Tool result"
            mock_auth.assert_called_once_with("test-fragment", "user-jwt", "tenant-sub")
            mock_session_instance.call_tool.assert_called_once_with(
                "test-tool", {"param1": "value1"}
            )

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
            patch(
                "sap_cloud_sdk.agentgateway._lob.get_user_auth", new_callable=AsyncMock
            ) as mock_auth,
            patch("sap_cloud_sdk.agentgateway._lob.httpx.AsyncClient") as mock_http,
            patch(
                "sap_cloud_sdk.agentgateway._lob.streamable_http_client"
            ) as mock_stream,
            patch("sap_cloud_sdk.agentgateway._lob.ClientSession") as mock_session,
        ):
            mock_auth.return_value = "Bearer user-token"

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

            result = await call_mcp_tool_lob(tool, "user-jwt", "tenant-sub")

            assert result == ""
