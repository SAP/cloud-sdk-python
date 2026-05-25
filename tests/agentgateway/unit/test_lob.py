"""Unit tests for LoB agent flow."""

import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from sap_cloud_sdk.agentgateway._lob import (
    _ias_dest_name,
    _fetch_auth_token,
    list_mcp_fragments,
    get_ias_fragment_name,
    get_ias_user_fragment_name,
    fetch_system_auth,
    fetch_user_auth,
    get_mcp_tools_lob,
    call_mcp_tool_lob,
    _LABEL_KEY,
    _MCP_LABEL_VALUE,
    _IAS_LABEL_VALUE,
    _IAS_USER_LABEL_VALUE,
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
# Test: get_ias_user_fragment_name
# ============================================================


class TestGetIasUserFragmentName:
    """Tests for get_ias_user_fragment_name function."""

    def test_returns_fragment_name(self):
        """Return name of first IAS user fragment found."""
        fragment = MagicMock()
        fragment.name = "sap-managed-runtime-agw-subscriber-ias-user-abc123"

        with patch("sap_cloud_sdk.agentgateway._lob.create_fragment_client") as mock_client:
            mock_client.return_value.list_instance_fragments.return_value = [fragment]

            result = get_ias_user_fragment_name("tenant-sub")

            assert result == "sap-managed-runtime-agw-subscriber-ias-user-abc123"

    def test_uses_correct_filter_labels(self):
        """Use correct label filter for IAS user fragments."""
        fragment = MagicMock()
        fragment.name = "ias-user-fragment"

        with patch("sap_cloud_sdk.agentgateway._lob.create_fragment_client") as mock_client:
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
        with patch("sap_cloud_sdk.agentgateway._lob.create_fragment_client") as mock_client:
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
