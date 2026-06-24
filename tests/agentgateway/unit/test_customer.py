"""Unit tests for customer agent flow."""

import json
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from sap_cloud_sdk.agentgateway._customer import (
    detect_customer_agent_credentials,
    load_customer_credentials,
    load_customer_credentials_from_env,
    get_system_token_mtls,
    get_system_token_transparent,
    exchange_user_token,
    exchange_user_token_transparent,
    get_mcp_tools_customer,
    call_mcp_tool_customer,
    _build_mcp_url,
    _request_token_transparent,
    _CREDENTIALS_PATH_ENV,
    _CREDENTIALS_DEFAULT_PATH,
    _ENV_CLIENT_ID,
    _ENV_TOKEN_SERVICE_URL,
    _ENV_GATEWAY_URL,
    _ENV_INTEGRATION_DEPENDENCIES,
)
from sap_cloud_sdk.agentgateway._models import (
    CustomerCredentials,
    IntegrationDependency,
    MCPTool,
)
from sap_cloud_sdk.agentgateway._token_cache import _TokenCache
from sap_cloud_sdk.agentgateway.config import ClientConfig, TlsMode
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError


# ============================================================
# Test: detect_customer_agent_credentials
# ============================================================


class TestDetectCustomerAgentCredentials:
    """Tests for customer agent credential detection."""

    def test_detect_from_env_var_path(self, tmp_path):
        """Detect credentials from path specified in environment variable."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text('{"clientid": "test"}')

        with patch.dict(os.environ, {_CREDENTIALS_PATH_ENV: str(creds_file)}):
            result = detect_customer_agent_credentials()
            assert result == str(creds_file)

    def test_detect_from_env_var_path_file_not_exists(self):
        """Return None when env var path doesn't exist."""
        with patch.dict(os.environ, {_CREDENTIALS_PATH_ENV: "/nonexistent/path"}):
            result = detect_customer_agent_credentials()
            assert result is None

    def test_detect_from_default_path(self):
        """Detect credentials from default mounted path."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove env var if present
            os.environ.pop(_CREDENTIALS_PATH_ENV, None)

            with patch("os.path.isfile") as mock_isfile:
                mock_isfile.side_effect = lambda p: p == _CREDENTIALS_DEFAULT_PATH

                result = detect_customer_agent_credentials()
                assert result == _CREDENTIALS_DEFAULT_PATH

    def test_no_credentials_returns_none(self):
        """Return None when no credentials are found."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(_CREDENTIALS_PATH_ENV, None)

            with patch("os.path.isfile", return_value=False):
                result = detect_customer_agent_credentials()
                assert result is None

    def test_env_var_takes_priority_over_default(self, tmp_path):
        """Env var path should take priority over default path."""
        creds_file = tmp_path / "custom_credentials.json"
        creds_file.write_text('{"clientid": "custom"}')

        with patch.dict(os.environ, {_CREDENTIALS_PATH_ENV: str(creds_file)}):
            # Even if default path exists, env var should be used
            with patch("os.path.isfile") as mock_isfile:

                def isfile_side_effect(path):
                    if path == str(creds_file):
                        return True
                    if path == _CREDENTIALS_DEFAULT_PATH:
                        return True
                    return False

                mock_isfile.side_effect = isfile_side_effect

                result = detect_customer_agent_credentials()
                assert result == str(creds_file)


# ============================================================
# Test: load_customer_credentials
# ============================================================


class TestLoadCustomerCredentials:
    """Tests for loading customer credentials from file."""

    def test_loads_valid_credentials(self, tmp_path):
        """Load credentials from valid JSON file."""
        creds_file = tmp_path / "credentials.json"
        creds_data = {
            "tokenServiceUrl": "https://ias.example.com/oauth2/token",
            "clientid": "my-client-id",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "privateKey": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "gatewayUrl": "https://agw.example.com/v1/mcp/",
            "integrationDependencies": [
                {
                    "ordId": "sap.test:apiResource:demo:v1",
                    "data": {"globalTenantId": "123"},
                },
            ],
        }
        creds_file.write_text(json.dumps(creds_data))

        result = load_customer_credentials(str(creds_file))

        assert result.token_service_url == "https://ias.example.com/oauth2/token"
        assert result.client_id == "my-client-id"
        assert (
            result.certificate
            == "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"
        )
        assert (
            result.private_key
            == "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        )
        assert (
            result.gateway_url == "https://agw.example.com/v1/mcp"
        )  # trailing slash stripped

    def test_raises_on_missing_required_field(self, tmp_path):
        """Raise error when required field is missing."""
        creds_file = tmp_path / "credentials.json"
        creds_data = {
            "tokenServiceUrl": "https://ias.example.com/oauth2/token",
            "clientid": "my-client-id",
            # Missing certificate, privateKey, gatewayUrl
        }
        creds_file.write_text(json.dumps(creds_data))

        with pytest.raises(AgentGatewaySDKError, match="missing required fields"):
            load_customer_credentials(str(creds_file))

    def test_raises_on_invalid_json(self, tmp_path):
        """Raise error when file contains invalid JSON."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("not valid json")

        with pytest.raises(AgentGatewaySDKError, match="Failed to load credentials"):
            load_customer_credentials(str(creds_file))

    def test_raises_on_file_not_found(self):
        """Raise error when file doesn't exist."""
        with pytest.raises(AgentGatewaySDKError, match="Failed to load credentials"):
            load_customer_credentials("/nonexistent/path/credentials.json")

    def test_loads_integration_dependencies(self, tmp_path):
        """Load integrationDependencies when present in credentials."""
        creds_file = tmp_path / "credentials.json"
        creds_data = {
            "tokenServiceUrl": "https://ias.example.com/oauth2/token",
            "clientid": "my-client-id",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "privateKey": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "gatewayUrl": "https://agw.example.com",
            "integrationDependencies": [
                {
                    "ordId": "sap.mcpbuilder:apiResource:cost-center:v1",
                    "data": {"globalTenantId": "250695"},
                },
                {
                    "ordId": "sap.flights:mcpServer:v1",
                    "data": {"globalTenantId": "892451733"},
                },
            ],
        }
        creds_file.write_text(json.dumps(creds_data))

        result = load_customer_credentials(str(creds_file))

        assert result.integration_dependencies is not None
        assert len(result.integration_dependencies) == 2
        assert (
            result.integration_dependencies[0].ord_id
            == "sap.mcpbuilder:apiResource:cost-center:v1"
        )
        assert result.integration_dependencies[0].global_tenant_id == "250695"
        assert result.integration_dependencies[1].ord_id == "sap.flights:mcpServer:v1"
        assert result.integration_dependencies[1].global_tenant_id == "892451733"

    def test_raises_when_integration_dependencies_missing(self, tmp_path):
        """Raise error when integrationDependencies is not in credentials file."""
        creds_file = tmp_path / "credentials.json"
        creds_data = {
            "tokenServiceUrl": "https://ias.example.com/oauth2/token",
            "clientid": "my-client-id",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "privateKey": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "gatewayUrl": "https://agw.example.com",
        }
        creds_file.write_text(json.dumps(creds_data))

        with pytest.raises(
            AgentGatewaySDKError,
            match="missing required field: integrationDependencies",
        ):
            load_customer_credentials(str(creds_file))

    def test_raises_on_invalid_integration_dependencies_format(self, tmp_path):
        """Raise error when integrationDependencies has invalid format."""
        creds_file = tmp_path / "credentials.json"
        creds_data = {
            "tokenServiceUrl": "https://ias.example.com/oauth2/token",
            "clientid": "my-client-id",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "privateKey": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "gatewayUrl": "https://agw.example.com",
            "integrationDependencies": [
                {"ordId": "missing-data-field"},  # Missing 'data' key
            ],
        }
        creds_file.write_text(json.dumps(creds_data))

        with pytest.raises(
            AgentGatewaySDKError, match="Failed to parse integrationDependencies"
        ):
            load_customer_credentials(str(creds_file))


# ============================================================
# Test: _build_mcp_url
# ============================================================


class TestBuildMcpUrl:
    """Tests for MCP URL construction."""

    def test_builds_url_without_v1_mcp(self):
        """Build URL when gateway_url doesn't include /v1/mcp."""
        result = _build_mcp_url(
            gateway_url="https://agw.example.com",
            ord_id="sap.mcpbuilder:apiResource:cost-center:v1",
            gt_id="250695",
        )

        assert (
            result
            == "https://agw.example.com/v1/mcp/sap.mcpbuilder:apiResource:cost-center:v1/250695"
        )

    def test_builds_url_with_v1_mcp(self):
        """Build URL when gateway_url already includes /v1/mcp."""
        result = _build_mcp_url(
            gateway_url="https://agw.example.com/v1/mcp",
            ord_id="sap.mcpbuilder:apiResource:sales-order:v1",
            gt_id="892451733",
        )

        assert (
            result
            == "https://agw.example.com/v1/mcp/sap.mcpbuilder:apiResource:sales-order:v1/892451733"
        )


# ============================================================
# Test: get_system_token_mtls
# ============================================================


class TestGetSystemTokenMtls:
    """Tests for mTLS system token acquisition."""

    @pytest.fixture
    def credentials(self):
        """Create test credentials."""
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            private_key="-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            gateway_url="https://agw.example.com",
            integration_dependencies=[],
        )

    def test_requests_client_credentials_token(self, credentials):
        """Request system token using client credentials grant."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "system-token-123"}

        with (
            patch(
                "sap_cloud_sdk.agentgateway._customer._create_ssl_context"
            ) as mock_ssl,
            patch("httpx.Client") as mock_client_class,
        ):
            mock_ssl.return_value = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = get_system_token_mtls(credentials, timeout=60.0)

            assert result == "system-token-123"
            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert "grant_type" in str(call_kwargs)

    def test_raises_on_failed_request(self, credentials):
        """Raise error when token request fails."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with (
            patch(
                "sap_cloud_sdk.agentgateway._customer._create_ssl_context"
            ) as mock_ssl,
            patch("httpx.Client") as mock_client_class,
        ):
            mock_ssl.return_value = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(AgentGatewaySDKError, match="Token request failed"):
                get_system_token_mtls(credentials, timeout=60.0)

    def test_reuses_cached_system_token(self, credentials):
        """Reuse cached system token until it expires."""
        token_cache = _TokenCache(ClientConfig())

        with patch(
            "sap_cloud_sdk.agentgateway._customer._request_token_mtls",
            return_value={"access_token": "system-token-123", "expires_in": 300},
        ) as mock_request:
            first = get_system_token_mtls(
                credentials, timeout=60.0, token_cache=token_cache
            )
            second = get_system_token_mtls(
                credentials, timeout=60.0, token_cache=token_cache
            )

        assert first == "system-token-123"
        assert second == "system-token-123"
        mock_request.assert_called_once()

    def test_scopes_system_token_cache_by_app_tid(self, credentials):
        """Keep app-tid-specific system tokens isolated in the cache."""
        token_cache = _TokenCache(ClientConfig())

        with patch(
            "sap_cloud_sdk.agentgateway._customer._request_token_mtls",
            side_effect=[
                {"access_token": "token-tid-1", "expires_in": 300},
                {"access_token": "token-tid-2", "expires_in": 300},
            ],
        ) as mock_request:
            first = get_system_token_mtls(
                credentials,
                timeout=60.0,
                app_tid="tid-1",
                token_cache=token_cache,
            )
            second = get_system_token_mtls(
                credentials,
                timeout=60.0,
                app_tid="tid-1",
                token_cache=token_cache,
            )
            third = get_system_token_mtls(
                credentials,
                timeout=60.0,
                app_tid="tid-2",
                token_cache=token_cache,
            )

        assert first == "token-tid-1"
        assert second == "token-tid-1"
        assert third == "token-tid-2"
        assert mock_request.call_count == 2


# ============================================================
# Test: exchange_user_token
# ============================================================


class TestExchangeUserToken:
    """Tests for user token exchange."""

    @pytest.fixture
    def credentials(self):
        """Create test credentials."""
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            private_key="-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            gateway_url="https://agw.example.com",
            integration_dependencies=[],
        )

    def test_exchanges_user_token_with_jwt_bearer(self, credentials):
        """Exchange user token using jwt-bearer grant."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "exchanged-token-123"}

        with (
            patch(
                "sap_cloud_sdk.agentgateway._customer._create_ssl_context"
            ) as mock_ssl,
            patch("httpx.Client") as mock_client_class,
        ):
            mock_ssl.return_value = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = exchange_user_token(credentials, "user-jwt-token", timeout=60.0)

            assert result == "exchanged-token-123"
            call_args = mock_client.post.call_args
            # Verify jwt-bearer grant type is used
            data = call_args.kwargs.get("data", {})
            assert data["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
            assert data["assertion"] == "user-jwt-token"

    def test_passes_app_tid_when_provided(self, credentials):
        """Include app_tid in request when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "token-with-tid"}

        with (
            patch(
                "sap_cloud_sdk.agentgateway._customer._create_ssl_context"
            ) as mock_ssl,
            patch("httpx.Client") as mock_client_class,
        ):
            mock_ssl.return_value = MagicMock()
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = exchange_user_token(
                credentials, "user-jwt", timeout=60.0, app_tid="test-tid"
            )

            assert result == "token-with-tid"
            call_args = mock_client.post.call_args
            data = call_args.kwargs.get("data", {})
            assert data["app_tid"] == "test-tid"

    def test_reuses_cached_user_token(self, credentials):
        """Reuse exchanged user token until it expires."""
        token_cache = _TokenCache(ClientConfig())

        with patch(
            "sap_cloud_sdk.agentgateway._customer._request_token_mtls",
            return_value={"access_token": "exchanged-token-123", "expires_in": 300},
        ) as mock_request:
            first = exchange_user_token(
                credentials,
                "user-jwt-token",
                timeout=60.0,
                token_cache=token_cache,
            )
            second = exchange_user_token(
                credentials,
                "user-jwt-token",
                timeout=60.0,
                token_cache=token_cache,
            )

        assert first == "exchanged-token-123"
        assert second == "exchanged-token-123"
        mock_request.assert_called_once()


# ============================================================
# Test: get_mcp_tools_customer
# ============================================================


class TestGetMcpToolsCustomer:
    """Tests for customer flow tool discovery."""

    @pytest.fixture
    def credentials(self):
        """Create test credentials."""
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="cert",
            private_key="key",
            gateway_url="https://agw.example.com",
            integration_dependencies=[
                IntegrationDependency(
                    ord_id="sap.mcpbuilder:apiResource:cost-center:v1",
                    global_tenant_id="250695",
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_raises_when_empty_dependencies(self):
        """Raise error when integrationDependencies is empty."""
        credentials = CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="cert",
            private_key="key",
            gateway_url="https://agw.example.com",
            integration_dependencies=[],
        )
        with pytest.raises(
            AgentGatewaySDKError, match="integrationDependencies is empty"
        ):
            await get_mcp_tools_customer(credentials, "system-token", 60.0)

    @pytest.mark.asyncio
    async def test_discovers_tools_from_credentials(self, credentials):
        """Discover tools from integrationDependencies using pre-fetched token."""
        mock_tools = [
            MCPTool(
                name="list_cost_centers",
                server_name="cost-center",
                description="List cost centers",
                input_schema={},
                url="https://agw.example.com/v1/mcp/sap.mcpbuilder:apiResource:cost-center:v1/250695",
            ),
        ]

        with (
            patch(
                "sap_cloud_sdk.agentgateway._customer._list_server_tools",
                new_callable=AsyncMock,
                return_value=mock_tools,
            ) as mock_list,
        ):
            result = await get_mcp_tools_customer(
                credentials, "pre-fetched-system-token", 60.0
            )

            assert len(result) == 1
            assert result[0].name == "list_cost_centers"
            mock_list.assert_called_once()
            # Verify the pre-fetched token was passed
            call_args = mock_list.call_args[0]
            assert call_args[1] == "pre-fetched-system-token"

    @pytest.mark.asyncio
    async def test_handles_server_error_gracefully(self):
        """Continue with other servers when one fails."""
        credentials = CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="cert",
            private_key="key",
            gateway_url="https://agw.example.com",
            integration_dependencies=[
                IntegrationDependency(ord_id="server1", global_tenant_id="111"),
                IntegrationDependency(ord_id="server2", global_tenant_id="222"),
            ],
        )

        mock_tool = MCPTool(
            name="tool2",
            server_name="server2",
            description="Tool 2",
            input_schema={},
            url="https://example.com",
        )

        call_count = 0

        async def mock_list_tools(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Server 1 failed")
            return [mock_tool]

        with (
            patch(
                "sap_cloud_sdk.agentgateway._customer._list_server_tools",
                side_effect=mock_list_tools,
            ),
        ):
            result = await get_mcp_tools_customer(
                credentials, "system-token", 60.0
            )

            # Should still return tools from server2
            assert len(result) == 1
            assert result[0].name == "tool2"


# ============================================================
# Test: call_mcp_tool_customer
# ============================================================


class TestCallMcpToolCustomer:
    """Tests for customer flow tool invocation."""

    @pytest.fixture
    def credentials(self):
        """Create test credentials."""
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="cert",
            private_key="key",
            gateway_url="https://agw.example.com",
            integration_dependencies=[
                IntegrationDependency(
                    ord_id="sap.mcpbuilder:apiResource:cost-center:v1",
                    global_tenant_id="250695",
                ),
            ],
        )

    @pytest.fixture
    def mock_tool(self):
        """Create a mock MCPTool."""
        return MCPTool(
            name="create_order",
            server_name="sales",
            description="Create a sales order",
            input_schema={
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
            },
            url="https://agw.example.com/v1/mcp/sales/250695",
        )

    @pytest.mark.asyncio
    async def test_calls_tool_with_pre_fetched_token(self, credentials, mock_tool):
        """Call tool using pre-fetched auth token."""
        with (
            patch(
                "httpx.AsyncClient",
            ) as mock_client_class,
            patch(
                "sap_cloud_sdk.agentgateway._customer.streamable_http_client",
            ) as mock_stream,
            patch(
                "sap_cloud_sdk.agentgateway._customer.ClientSession",
            ) as mock_session_class,
        ):
            # Set up mock chain
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_stream_ctx = AsyncMock()
            mock_stream_ctx.__aenter__ = AsyncMock(
                return_value=(AsyncMock(), AsyncMock(), None)
            )
            mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_stream.return_value = mock_stream_ctx

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock()
            mock_result = MagicMock()
            mock_content = MagicMock()
            mock_content.text = "Order created successfully"
            mock_result.content = [mock_content]
            mock_session.call_tool = AsyncMock(return_value=mock_result)
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_ctx

            result = await call_mcp_tool_customer(
                mock_tool, "pre-fetched-token", 60.0, order_id="12345"
            )

            assert result == "Order created successfully"
            # Verify the token was used in the Authorization header
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args.kwargs
            assert call_kwargs["headers"]["Authorization"] == "Bearer pre-fetched-token"

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_no_content(self, credentials, mock_tool):
        """Return empty string when tool returns no content."""
        with (
            patch(
                "httpx.AsyncClient",
            ) as mock_client_class,
            patch(
                "sap_cloud_sdk.agentgateway._customer.streamable_http_client",
            ) as mock_stream,
            patch(
                "sap_cloud_sdk.agentgateway._customer.ClientSession",
            ) as mock_session_class,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_stream_ctx = AsyncMock()
            mock_stream_ctx.__aenter__ = AsyncMock(
                return_value=(AsyncMock(), AsyncMock(), None)
            )
            mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_stream.return_value = mock_stream_ctx

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock()
            mock_result = MagicMock()
            mock_result.content = []
            mock_session.call_tool = AsyncMock(return_value=mock_result)
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_ctx

            result = await call_mcp_tool_customer(
                mock_tool, "auth-token", 60.0
            )

            assert result == ""


# ============================================================
# Test: detect_customer_agent_credentials — transparent mode
# ============================================================


class TestDetectCustomerAgentCredentialsTransparentMode:
    """Tests for credential detection when TlsMode.TRANSPARENT is active."""

    def test_transparent_mode_returns_none_immediately(self, tmp_path):
        """In transparent mode, credential file detection is skipped."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text('{"clientid": "test"}')

        with patch.dict(os.environ, {_CREDENTIALS_PATH_ENV: str(creds_file)}):
            result = detect_customer_agent_credentials(TlsMode.TRANSPARENT)

        assert result is None

    def test_transparent_mode_ignores_default_path(self):
        """In transparent mode, default credential path is not checked."""
        with patch("os.path.isfile", return_value=True):
            result = detect_customer_agent_credentials(TlsMode.TRANSPARENT)

        assert result is None

    def test_standard_mode_still_detects_file(self, tmp_path):
        """Standard mode (default) continues to detect credential files."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text('{"clientid": "test"}')

        with patch.dict(os.environ, {_CREDENTIALS_PATH_ENV: str(creds_file)}):
            result = detect_customer_agent_credentials(TlsMode.STANDARD)

        assert result == str(creds_file)


# ============================================================
# Test: load_customer_credentials_from_env
# ============================================================

_TRANSPARENT_ENV = {
    _ENV_CLIENT_ID: "test-client-id",
    _ENV_TOKEN_SERVICE_URL: "https://ias.example.com/oauth/token",
    _ENV_GATEWAY_URL: "https://agw.example.com",
}


class TestLoadCustomerCredentialsFromEnv:
    """Tests for loading customer credentials from environment variables."""

    def test_loads_required_fields(self):
        """Loads credentials from the three required environment variables."""
        with patch.dict(os.environ, _TRANSPARENT_ENV, clear=False):
            os.environ.pop(_ENV_INTEGRATION_DEPENDENCIES, None)
            creds = load_customer_credentials_from_env()

        assert creds.client_id == "test-client-id"
        assert creds.token_service_url == "https://ias.example.com/oauth/token"
        assert creds.gateway_url == "https://agw.example.com"
        assert creds.certificate is None
        assert creds.private_key is None
        assert creds.integration_dependencies == []

    def test_strips_trailing_slash_from_gateway_url(self):
        """Trailing slash is stripped from GATEWAY_URL."""
        env = {**_TRANSPARENT_ENV, _ENV_GATEWAY_URL: "https://agw.example.com/"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop(_ENV_INTEGRATION_DEPENDENCIES, None)
            creds = load_customer_credentials_from_env()

        assert creds.gateway_url == "https://agw.example.com"

    def test_parses_integration_dependencies(self):
        """INTEGRATION_DEPENDENCIES JSON array is parsed correctly."""
        deps = json.dumps([{"ordId": "sap.app:res:v1", "globalTenantId": "tenant-1"}])
        env = {**_TRANSPARENT_ENV, _ENV_INTEGRATION_DEPENDENCIES: deps}
        with patch.dict(os.environ, env, clear=False):
            creds = load_customer_credentials_from_env()

        assert len(creds.integration_dependencies) == 1
        assert creds.integration_dependencies[0].ord_id == "sap.app:res:v1"
        assert creds.integration_dependencies[0].global_tenant_id == "tenant-1"

    def test_missing_client_id_raises(self):
        """Missing CLIENT_ID raises AgentGatewaySDKError."""
        env = {
            _ENV_TOKEN_SERVICE_URL: "https://ias.example.com/oauth/token",
            _ENV_GATEWAY_URL: "https://agw.example.com",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop(_ENV_CLIENT_ID, None)
            with pytest.raises(AgentGatewaySDKError, match="transparent"):
                load_customer_credentials_from_env()

    def test_missing_token_service_url_raises(self):
        """Missing TOKEN_SERVICE_URL raises AgentGatewaySDKError."""
        env = {
            _ENV_CLIENT_ID: "test-client-id",
            _ENV_GATEWAY_URL: "https://agw.example.com",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop(_ENV_TOKEN_SERVICE_URL, None)
            with pytest.raises(AgentGatewaySDKError, match="transparent"):
                load_customer_credentials_from_env()

    def test_invalid_integration_dependencies_json_raises(self):
        """Invalid INTEGRATION_DEPENDENCIES JSON raises AgentGatewaySDKError."""
        env = {**_TRANSPARENT_ENV, _ENV_INTEGRATION_DEPENDENCIES: "not-json"}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(AgentGatewaySDKError, match="INTEGRATION_DEPENDENCIES"):
                load_customer_credentials_from_env()


# ============================================================
# Test: _request_token_transparent
# ============================================================


class TestRequestTokenTransparent:
    """Tests for token requests in transparent TLS mode."""

    def _make_credentials(self) -> CustomerCredentials:
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth/token",
            client_id="test-client-id",
            certificate=None,
            private_key=None,
            gateway_url="https://agw.example.com",
            integration_dependencies=[],
        )

    def test_no_ssl_context_used(self):
        """In transparent mode, httpx.Client is created without verify/ssl_context."""
        creds = self._make_credentials()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "token123", "expires_in": 3600}

        with patch("httpx.Client") as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.return_value = mock_response
            mock_client_class.return_value = mock_client_instance

            result = _request_token_transparent(creds, "client_credentials", 60.0)

        assert result["access_token"] == "token123"
        call_kwargs = mock_client_class.call_args.kwargs
        assert "verify" not in call_kwargs, "SSL context must not be passed in transparent mode"

    def test_request_body_contains_client_id(self):
        """Token request body includes client_id from credentials."""
        creds = self._make_credentials()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "token123", "expires_in": 3600}

        with patch("httpx.Client") as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.return_value = mock_response
            mock_client_class.return_value = mock_client_instance

            _request_token_transparent(creds, "client_credentials", 60.0)

        post_kwargs = mock_client_instance.post.call_args.kwargs
        assert post_kwargs["data"]["client_id"] == "test-client-id"
        assert post_kwargs["data"]["grant_type"] == "client_credentials"

    def test_non_200_status_raises(self):
        """Non-200 response raises AgentGatewaySDKError."""
        creds = self._make_credentials()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.Client") as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_instance.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.return_value = mock_response
            mock_client_class.return_value = mock_client_instance

            with pytest.raises(AgentGatewaySDKError, match="401"):
                _request_token_transparent(creds, "client_credentials", 60.0)


# ============================================================
# Test: get_system_token_transparent
# ============================================================


class TestGetSystemTokenTransparent:
    """Tests for system token acquisition in transparent mode."""

    def _make_credentials(self) -> CustomerCredentials:
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth/token",
            client_id="test-client-id",
            certificate=None,
            private_key=None,
            gateway_url="https://agw.example.com",
            integration_dependencies=[],
        )

    def test_returns_access_token(self):
        """Returns access token from token response."""
        creds = self._make_credentials()
        with patch(
            "sap_cloud_sdk.agentgateway._customer._request_token_transparent",
            return_value={"access_token": "system-token", "expires_in": 3600},
        ):
            token = get_system_token_transparent(creds, 60.0)

        assert token == "system-token"

    def test_uses_cache_when_available(self):
        """Returns cached token without making a new request."""
        creds = self._make_credentials()
        config = ClientConfig()
        cache = _TokenCache(config)
        scope_key = f"customer::{creds.client_id}::"
        cache.set_system_token("cached-token", float("inf"), scope_key)

        with patch(
            "sap_cloud_sdk.agentgateway._customer._request_token_transparent"
        ) as mock_req:
            token = get_system_token_transparent(creds, 60.0, token_cache=cache)

        assert token == "cached-token"
        mock_req.assert_not_called()


# ============================================================
# Test: exchange_user_token_transparent
# ============================================================


class TestExchangeUserTokenTransparent:
    """Tests for user token exchange in transparent mode."""

    def _make_credentials(self) -> CustomerCredentials:
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth/token",
            client_id="test-client-id",
            certificate=None,
            private_key=None,
            gateway_url="https://agw.example.com",
            integration_dependencies=[],
        )

    def test_returns_exchanged_token(self):
        """Returns exchanged access token."""
        creds = self._make_credentials()
        with patch(
            "sap_cloud_sdk.agentgateway._customer._request_token_transparent",
            return_value={"access_token": "user-token", "expires_in": 3600},
        ) as mock_req:
            token = exchange_user_token_transparent(creds, "user-jwt", 60.0)

        assert token == "user-token"
        call_kwargs = mock_req.call_args
        assert call_kwargs.kwargs["extra_data"]["assertion"] == "user-jwt"
        assert call_kwargs.kwargs["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
