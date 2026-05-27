"""Unit tests for LoB agent flow."""

import os
import time
from unittest.mock import patch, MagicMock, AsyncMock

import httpx
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
from sap_cloud_sdk.agentgateway._token_cache import _TokenCache
from sap_cloud_sdk.agentgateway._models import MCPTool
from sap_cloud_sdk.agentgateway.config import ClientConfig
from sap_cloud_sdk.agentgateway.exceptions import MCPServerNotFoundError
from sap_cloud_sdk.destination import ConsumptionLevel


def _make_cache() -> _TokenCache:
    return _TokenCache(ClientConfig())


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
    async def test_fetches_system_auth_on_cache_miss(self):
        """Fetch system auth from Destination Service on cache miss."""
        cache = _make_cache()

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

                result = await get_system_auth("tenant-sub", cache)

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

    @pytest.mark.asyncio
    async def test_returns_cached_token_without_fetching(self):
        """Return cached token without calling Destination Service."""
        cache = _make_cache()
        cache.set_system_token("Bearer cached-token", time.monotonic() + 600, "tenant-sub")

        with (
            patch("sap_cloud_sdk.agentgateway._lob.get_ias_fragment_name") as mock_ias,
            patch("sap_cloud_sdk.agentgateway._lob._fetch_auth_token") as mock_fetch,
        ):
            result = await get_system_auth("tenant-sub", cache)

            assert result == "Bearer cached-token"
            mock_ias.assert_not_called()
            mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_caches_fetched_token(self):
        """Store fetched token in cache so subsequent calls hit cache."""
        cache = _make_cache()

        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            with (
                patch("sap_cloud_sdk.agentgateway._lob.get_ias_fragment_name") as mock_ias,
                patch("sap_cloud_sdk.agentgateway._lob._fetch_auth_token") as mock_fetch,
            ):
                mock_ias.return_value = "ias-frag"
                mock_fetch.return_value = "Bearer fresh-token"

                await get_system_auth("tenant-sub", cache)
                # Second call should hit cache
                result = await get_system_auth("tenant-sub", cache)

                assert result == "Bearer fresh-token"
                mock_fetch.assert_called_once()  # only one Destination Service call


# ============================================================
# Test: get_user_auth
# ============================================================


class TestGetUserAuth:
    """Tests for get_user_auth async function."""

    @pytest.mark.asyncio
    async def test_fetches_user_auth_on_cache_miss(self):
        """Fetch user auth with token exchange on cache miss."""
        cache = _make_cache()

        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            with patch(
                "sap_cloud_sdk.agentgateway._lob._fetch_auth_token"
            ) as mock_fetch:
                mock_fetch.return_value = "Bearer user-token"

                result = await get_user_auth("mcp-fragment", "user-jwt", "tenant-sub", cache)

                assert result == "Bearer user-token"
                mock_fetch.assert_called_once()
                call_args = mock_fetch.call_args
                assert call_args[0][0] == "sap-managed-runtime-ias-eu10"
                assert call_args[0][1] == "tenant-sub"
                options = call_args[0][2]
                assert options.user_token == "user-jwt"
                assert options.fragment_name == "mcp-fragment"
                assert options.fragment_level == ConsumptionLevel.INSTANCE

    @pytest.mark.asyncio
    async def test_returns_cached_user_token_without_fetching(self):
        """Return cached user token without calling Destination Service."""
        cache = _make_cache()
        scope_key = "mcp-fragment|tenant-sub"
        cache.set_user_token("user-jwt", "Bearer cached-user-token", time.monotonic() + 600, scope_key)

        with patch("sap_cloud_sdk.agentgateway._lob._fetch_auth_token") as mock_fetch:
            result = await get_user_auth("mcp-fragment", "user-jwt", "tenant-sub", cache)

            assert result == "Bearer cached-user-token"
            mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_caches_fetched_user_token(self):
        """Store fetched user token in cache so subsequent calls hit cache."""
        cache = _make_cache()

        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            with patch(
                "sap_cloud_sdk.agentgateway._lob._fetch_auth_token"
            ) as mock_fetch:
                mock_fetch.return_value = "Bearer fresh-user-token"

                await get_user_auth("mcp-fragment", "user-jwt", "tenant-sub", cache)
                result = await get_user_auth("mcp-fragment", "user-jwt", "tenant-sub", cache)

                assert result == "Bearer fresh-user-token"
                mock_fetch.assert_called_once()  # only one Destination Service call

    @pytest.mark.asyncio
    async def test_user_tokens_isolated_by_fragment(self):
        """Different fragments produce separate cache entries."""
        cache = _make_cache()

        with patch.dict(os.environ, {"APPFND_CONHOS_LANDSCAPE": "eu10"}):
            with patch(
                "sap_cloud_sdk.agentgateway._lob._fetch_auth_token"
            ) as mock_fetch:
                mock_fetch.side_effect = ["Bearer token-frag-a", "Bearer token-frag-b"]

                result_a = await get_user_auth("frag-a", "user-jwt", "tenant-sub", cache)
                result_b = await get_user_auth("frag-b", "user-jwt", "tenant-sub", cache)

                assert result_a == "Bearer token-frag-a"
                assert result_b == "Bearer token-frag-b"
                assert mock_fetch.call_count == 2


# ============================================================
# Test: get_mcp_tools_lob
# ============================================================


class TestGetMcpToolsLob:
    """Tests for get_mcp_tools_lob async function."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_fragments(self):
        """Return empty list when no fragments found."""
        cache = _make_cache()

        with patch("sap_cloud_sdk.agentgateway._lob.list_mcp_fragments") as mock_list:
            mock_list.return_value = []

            result = await get_mcp_tools_lob("tenant-sub", 60.0, cache)

            assert result == []

    @pytest.mark.asyncio
    async def test_skips_fragments_without_url(self):
        """Skip fragments that don't have URL property."""
        cache = _make_cache()
        fragment = MagicMock()
        fragment.name = "mcp-server-a"
        fragment.properties = {}  # No URL

        with patch("sap_cloud_sdk.agentgateway._lob.list_mcp_fragments") as mock_list:
            mock_list.return_value = [fragment]

            result = await get_mcp_tools_lob("tenant-sub", 60.0, cache)

            assert result == []

    @pytest.mark.asyncio
    async def test_uses_fragment_name_directly(self):
        """Use fragment name as-is (no -technical stripping)."""
        cache = _make_cache()
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

            await get_mcp_tools_lob("tenant-sub", 60.0, cache)

            mock_auth.assert_called_once_with("tenant-sub", cache)
            mock_tools.assert_called_once()
            call_args = mock_tools.call_args[0]
            assert call_args[2] == "mcp-server-a"

    @pytest.mark.asyncio
    async def test_reuses_system_auth_across_fragments(self):
        """Fetch system auth once and reuse for all fragments."""
        cache = _make_cache()
        fragment1 = MagicMock()
        fragment1.name = "frag-1"
        fragment1.properties = {"URL": "https://example1.com/mcp"}

        fragment2 = MagicMock()
        fragment2.name = "frag-2"
        fragment2.properties = {"URL": "https://example2.com/mcp"}

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
            mock_auth.return_value = "Bearer token"
            mock_tools.return_value = []

            await get_mcp_tools_lob("tenant-sub", 60.0, cache)

            # get_system_auth called once — result reused for second fragment
            mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_non_401_exception_for_single_fragment(self):
        """Continue processing other fragments when list_server_tools fails (non-401)."""
        cache = _make_cache()
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
            mock_auth.return_value = "Bearer token"
            mock_tools.side_effect = [Exception("Connection refused"), [mock_tool]]

            result = await get_mcp_tools_lob("tenant-sub", 60.0, cache)

            assert len(result) == 1
            assert result[0].name == "tool2"

    @pytest.mark.asyncio
    async def test_retries_on_401_and_succeeds(self):
        """On 401 from list_server_tools: invalidate system token, retry, succeed."""
        cache = _make_cache()
        fragment = MagicMock()
        fragment.name = "mcp-server"
        fragment.properties = {"URL": "https://example.com/mcp"}

        mock_tool = MCPTool(
            name="tool",
            server_name="server",
            description="Test",
            input_schema={},
            url="https://example.com/mcp",
            fragment_name="mcp-server",
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        unauthorized = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

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
            mock_auth.side_effect = ["Bearer stale-token", "Bearer fresh-token"]
            mock_tools.side_effect = [unauthorized, [mock_tool]]

            result = await get_mcp_tools_lob("tenant-sub", 60.0, cache)

            assert len(result) == 1
            assert mock_auth.call_count == 2
            assert mock_tools.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_fragment_after_two_401s(self):
        """On 401 on both attempts: skip fragment, continue with others."""
        cache = _make_cache()
        fragment1 = MagicMock()
        fragment1.name = "bad-server"
        fragment1.properties = {"URL": "https://bad.example.com/mcp"}

        fragment2 = MagicMock()
        fragment2.name = "good-server"
        fragment2.properties = {"URL": "https://good.example.com/mcp"}

        mock_tool = MCPTool(
            name="good-tool",
            server_name="good-server",
            description="Test",
            input_schema={},
            url="https://good.example.com/mcp",
            fragment_name="good-server",
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        unauthorized = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

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
            mock_auth.return_value = "Bearer token"
            # fragment1: 401 on both attempts; fragment2: success
            mock_tools.side_effect = [unauthorized, unauthorized, [mock_tool]]

            result = await get_mcp_tools_lob("tenant-sub", 60.0, cache)

            assert len(result) == 1
            assert result[0].name == "good-tool"


# ============================================================
# Test: call_mcp_tool_lob
# ============================================================


class TestCallMcpToolLob:
    """Tests for call_mcp_tool_lob async function."""

    @pytest.mark.asyncio
    async def test_calls_tool_with_user_auth(self):
        """Call tool using user authentication."""
        cache = _make_cache()
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
                tool, "user-jwt", "tenant-sub", 60.0, cache, param1="value1"
            )

            assert result == "Tool result"
            mock_auth.assert_called_once_with(
                "test-fragment", "user-jwt", "tenant-sub", cache
            )
            mock_session_instance.call_tool.assert_called_once_with(
                "test-tool", {"param1": "value1"}
            )

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_no_content(self):
        """Return empty string when tool returns no content."""
        cache = _make_cache()
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

            result = await call_mcp_tool_lob(tool, "user-jwt", "tenant-sub", 60.0, cache)

            assert result == ""

    @pytest.mark.asyncio
    async def test_retries_on_401_and_succeeds(self):
        """On 401 from MCP server: invalidate cached user token, retry, succeed."""
        cache = _make_cache()
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
        mock_result.content[0].text = "Success after retry"

        mock_response = MagicMock()
        mock_response.status_code = 401
        unauthorized = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

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
            mock_auth.side_effect = ["Bearer stale-token", "Bearer fresh-token"]

            mock_http_instance = AsyncMock()
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_http.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_stream.return_value.__aenter__ = AsyncMock(
                return_value=(AsyncMock(), AsyncMock(), None)
            )
            mock_stream.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_session_instance = AsyncMock()
            mock_session_instance.initialize = AsyncMock()
            mock_session_instance.call_tool = AsyncMock(
                side_effect=[unauthorized, mock_result]
            )
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session_instance
            )
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await call_mcp_tool_lob(
                tool, "user-jwt", "tenant-sub", 60.0, cache
            )

            assert result == "Success after retry"
            assert mock_auth.call_count == 2

    @pytest.mark.asyncio
    async def test_invalidates_user_token_on_401(self):
        """On 401: invalidate the user token in cache before retry."""
        cache = _make_cache()
        scope_key = "test-fragment|tenant-sub"
        cache.set_user_token(
            "user-jwt", "Bearer stale-token", time.monotonic() + 600, scope_key
        )

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
        mock_result.content[0].text = "ok"

        mock_response = MagicMock()
        mock_response.status_code = 401
        unauthorized = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

        call_count = 0

        async def _fake_get_user_auth(fragment, user_tok, tenant, c):
            nonlocal call_count
            call_count += 1
            # After invalidation the cache entry is gone; simulate fresh fetch
            return "Bearer fresh-token"

        with (
            patch(
                "sap_cloud_sdk.agentgateway._lob.get_user_auth",
                side_effect=_fake_get_user_auth,
            ),
            patch("sap_cloud_sdk.agentgateway._lob.httpx.AsyncClient") as mock_http,
            patch(
                "sap_cloud_sdk.agentgateway._lob.streamable_http_client"
            ) as mock_stream,
            patch("sap_cloud_sdk.agentgateway._lob.ClientSession") as mock_session,
        ):
            mock_http_instance = AsyncMock()
            mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_http.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_stream.return_value.__aenter__ = AsyncMock(
                return_value=(AsyncMock(), AsyncMock(), None)
            )
            mock_stream.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_session_instance = AsyncMock()
            mock_session_instance.initialize = AsyncMock()
            mock_session_instance.call_tool = AsyncMock(
                side_effect=[unauthorized, mock_result]
            )
            mock_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session_instance
            )
            mock_session.return_value.__aexit__ = AsyncMock(return_value=False)

            await call_mcp_tool_lob(tool, "user-jwt", "tenant-sub", 60.0, cache)

            # Cache entry was invalidated before retry
            assert cache.get_user_token("user-jwt", scope_key) is None
            assert call_count == 2
