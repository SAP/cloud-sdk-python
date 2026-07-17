"""Unit tests for customer agent flow."""

import json
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from sap_cloud_sdk.agentgateway._customer import (
    detect_customer_agent_credentials,
    detect_transparent_credentials,
    load_customer_credentials,
    load_customer_credentials_from_env,
    get_system_token_mtls,
    exchange_user_token,
    get_mcp_tools_customer,
    call_mcp_tool_customer,
    _build_mcp_url,
    _INTEGRATION_CLIENT_ID_ENV,
    _INTEGRATION_AUTH_URL_ENV,
    _INTEGRATION_GATEWAY_URL_ENV,
)
from sap_cloud_sdk.agentgateway._models import (
    CustomerCredentials,
    IntegrationDependency,
    MCPTool,
)
from sap_cloud_sdk.agentgateway._token_cache import _TokenCache
from sap_cloud_sdk.agentgateway.config import ClientConfig
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError


# ============================================================
# Test: detect_customer_agent_credentials
# ============================================================


class TestDetectCustomerAgentCredentials:
    """Tests for customer agent credential detection."""

    def test_detect_from_servicebinding_root(self, tmp_path):
        """Detect credentials via servicebinding.io scan of SERVICE_BINDING_ROOT."""
        binding_dir = tmp_path / "my-binding"
        binding_dir.mkdir()
        (binding_dir / "type").write_text("integration-credentials")
        creds_file = binding_dir / "credentials"
        creds_file.write_text('{"clientid": "test"}')

        with patch(
            "sap_cloud_sdk.agentgateway._customer.resolve_base_mount",
            return_value=str(tmp_path),
        ):
            result = detect_customer_agent_credentials()
            assert result == str(creds_file)

    def test_skips_binding_with_wrong_type(self, tmp_path):
        """Return None when binding type does not match integration-credentials."""
        binding_dir = tmp_path / "other-binding"
        binding_dir.mkdir()
        (binding_dir / "type").write_text("some-other-type")
        (binding_dir / "credentials").write_text('{"clientid": "test"}')

        with patch(
            "sap_cloud_sdk.agentgateway._customer.resolve_base_mount",
            return_value=str(tmp_path),
        ):
            result = detect_customer_agent_credentials()
            assert result is None

    def test_no_credentials_returns_none(self):
        """Return None when SERVICE_BINDING_ROOT does not exist."""
        with patch(
            "sap_cloud_sdk.agentgateway._customer.resolve_base_mount",
            return_value=None,
        ):
            result = detect_customer_agent_credentials()
            assert result is None


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
                    "globalTenantId": "123",
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
                    "globalTenantId": "250695",
                },
                {
                    "ordId": "sap.flights:mcpServer:v1",
                    "globalTenantId": "892451733",
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

    def test_loads_integration_dependencies_flat_format(self, tmp_path):
        """Load integrationDependencies in flat format (globalTenantId at top level)."""
        creds_file = tmp_path / "credentials.json"
        creds_data = {
            "tokenServiceUrl": "https://ias.example.com/oauth2/token",
            "clientid": "my-client-id",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "privateKey": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "gatewayUrl": "https://agw.example.com",
            "integrationDependencies": [
                {
                    "ordId": "sap.s4:apiResource:API_PRODUCT:v1",
                    "globalTenantId": "731473562",
                },
            ],
        }
        creds_file.write_text(json.dumps(creds_data))

        result = load_customer_credentials(str(creds_file))

        assert len(result.integration_dependencies) == 1
        assert result.integration_dependencies[0].ord_id == "sap.s4:apiResource:API_PRODUCT:v1"
        assert result.integration_dependencies[0].global_tenant_id == "731473562"

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
# Test: detect_transparent_credentials
# ============================================================


class TestDetectTransparentCredentials:
    """Tests for transparent mode credential detection."""

    def test_detects_when_all_env_vars_present(self):
        """Detect transparent mode when all required environment variables are set."""
        with patch.dict(
            os.environ,
            {
                _INTEGRATION_CLIENT_ID_ENV: "test-client",
                _INTEGRATION_AUTH_URL_ENV: "https://ias.example.com/oauth2/token",
                _INTEGRATION_GATEWAY_URL_ENV: "https://agw.example.com",
            },
        ):
            result = detect_transparent_credentials()
            assert result is True

    def test_returns_false_when_client_id_missing(self):
        """Return False when INTEGRATION_CLIENT_ID is missing."""
        with patch.dict(
            os.environ,
            {
                _INTEGRATION_AUTH_URL_ENV: "https://ias.example.com/oauth2/token",
                _INTEGRATION_GATEWAY_URL_ENV: "https://agw.example.com",
            },
            clear=False,
        ):
            os.environ.pop(_INTEGRATION_CLIENT_ID_ENV, None)
            result = detect_transparent_credentials()
            assert result is False

    def test_returns_false_when_token_service_url_missing(self):
        """Return False when INTEGRATION_TOKEN_SERVICE_URL is missing."""
        with patch.dict(
            os.environ,
            {
                _INTEGRATION_CLIENT_ID_ENV: "test-client",
                _INTEGRATION_GATEWAY_URL_ENV: "https://agw.example.com",
            },
            clear=False,
        ):
            os.environ.pop(_INTEGRATION_AUTH_URL_ENV, None)
            result = detect_transparent_credentials()
            assert result is False

    def test_returns_false_when_gateway_url_missing(self):
        """Return False when INTEGRATION_GATEWAY_URL is missing."""
        with patch.dict(
            os.environ,
            {
                _INTEGRATION_CLIENT_ID_ENV: "test-client",
                _INTEGRATION_AUTH_URL_ENV: "https://ias.example.com/oauth2/token",
            },
            clear=False,
        ):
            os.environ.pop(_INTEGRATION_GATEWAY_URL_ENV, None)
            result = detect_transparent_credentials()
            assert result is False

    def test_returns_false_when_all_missing(self):
        """Return False when all environment variables are missing."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(_INTEGRATION_CLIENT_ID_ENV, None)
            os.environ.pop(_INTEGRATION_AUTH_URL_ENV, None)
            os.environ.pop(_INTEGRATION_GATEWAY_URL_ENV, None)
            result = detect_transparent_credentials()
            assert result is False


# ============================================================
# Test: load_customer_credentials_from_env
# ============================================================


class TestLoadCustomerCredentialsFromEnv:
    """Tests for loading credentials from environment variables (transparent mode)."""

    def test_loads_valid_credentials_from_env(self):
        """Load credentials from environment variables."""
        deps_json = json.dumps(
            [
                {
                    "ordId": "sap.example:apiResource:demo:v1",
                    "globalTenantId": "123456",
                }
            ]
        )

        with patch.dict(
            os.environ,
            {
                _INTEGRATION_CLIENT_ID_ENV: "test-client-id",
                _INTEGRATION_AUTH_URL_ENV: "https://ias.example.com/oauth2/token",
                _INTEGRATION_GATEWAY_URL_ENV: "https://agw.example.com/",
                "INTEGRATION_DEPENDENCIES": deps_json,
            },
        ):
            result = load_customer_credentials_from_env()

            assert result.client_id == "test-client-id"
            assert result.token_service_url == "https://ias.example.com/oauth2/token"
            assert result.gateway_url == "https://agw.example.com"
            assert result.certificate is None
            assert result.private_key is None
            assert len(result.integration_dependencies) == 1
            assert result.integration_dependencies[0].ord_id == "sap.example:apiResource:demo:v1"
            assert result.integration_dependencies[0].global_tenant_id == "123456"

    def test_raises_when_client_id_missing(self):
        """Raise error when INTEGRATION_CLIENT_ID is missing."""
        deps_json = json.dumps([{"ordId": "test", "globalTenantId": "123"}])

        with patch.dict(
            os.environ,
            {
                _INTEGRATION_AUTH_URL_ENV: "https://ias.example.com/oauth2/token",
                _INTEGRATION_GATEWAY_URL_ENV: "https://agw.example.com",
                "INTEGRATION_DEPENDENCIES": deps_json,
            },
            clear=False,
        ):
            os.environ.pop(_INTEGRATION_CLIENT_ID_ENV, None)

            with pytest.raises(
                AgentGatewaySDKError,
                match="Transparent TLS mode requires environment variables",
            ):
                load_customer_credentials_from_env()

    def test_raises_when_token_service_url_missing(self):
        """Raise error when INTEGRATION_TOKEN_SERVICE_URL is missing."""
        deps_json = json.dumps([{"ordId": "test", "globalTenantId": "123"}])

        with patch.dict(
            os.environ,
            {
                _INTEGRATION_CLIENT_ID_ENV: "test-client",
                _INTEGRATION_GATEWAY_URL_ENV: "https://agw.example.com",
                "INTEGRATION_DEPENDENCIES": deps_json,
            },
            clear=False,
        ):
            os.environ.pop(_INTEGRATION_AUTH_URL_ENV, None)

            with pytest.raises(
                AgentGatewaySDKError,
                match="Transparent TLS mode requires environment variables",
            ):
                load_customer_credentials_from_env()

    def test_raises_when_gateway_url_missing(self):
        """Raise error when INTEGRATION_GATEWAY_URL is missing."""
        deps_json = json.dumps([{"ordId": "test", "globalTenantId": "123"}])

        with patch.dict(
            os.environ,
            {
                _INTEGRATION_CLIENT_ID_ENV: "test-client",
                _INTEGRATION_AUTH_URL_ENV: "https://ias.example.com/oauth2/token",
                "INTEGRATION_DEPENDENCIES": deps_json,
            },
            clear=False,
        ):
            os.environ.pop(_INTEGRATION_GATEWAY_URL_ENV, None)

            with pytest.raises(
                AgentGatewaySDKError,
                match="Transparent TLS mode requires environment variables",
            ):
                load_customer_credentials_from_env()

    def test_raises_when_dependencies_missing(self):
        """Raise error when INTEGRATION_DEPENDENCIES is missing."""
        with patch.dict(
            os.environ,
            {
                _INTEGRATION_CLIENT_ID_ENV: "test-client",
                _INTEGRATION_AUTH_URL_ENV: "https://ias.example.com/oauth2/token",
                _INTEGRATION_GATEWAY_URL_ENV: "https://agw.example.com",
            },
            clear=False,
        ):
            os.environ.pop("INTEGRATION_DEPENDENCIES", None)

            with pytest.raises(
                AgentGatewaySDKError,
                match="Missing required environment variable: INTEGRATION_DEPENDENCIES",
            ):
                load_customer_credentials_from_env()

    def test_uses_custom_dependencies_resolver(self):
        """Use custom dependencies resolver when provided."""
        from sap_cloud_sdk.agentgateway._dependencies_resolver import (
            IntegrationDependenciesResolver,
        )

        class CustomResolver(IntegrationDependenciesResolver):
            def resolve(self):
                return [
                    IntegrationDependency(
                        ord_id="custom.ord:id:v1",
                        global_tenant_id="999",
                    )
                ]

        with patch.dict(
            os.environ,
            {
                _INTEGRATION_CLIENT_ID_ENV: "test-client",
                _INTEGRATION_AUTH_URL_ENV: "https://ias.example.com/oauth2/token",
                _INTEGRATION_GATEWAY_URL_ENV: "https://agw.example.com",
            },
        ):
            result = load_customer_credentials_from_env(
                dependencies_resolver=CustomResolver()
            )

            assert len(result.integration_dependencies) == 1
            assert result.integration_dependencies[0].ord_id == "custom.ord:id:v1"


# ============================================================
# Test: Transparent mode token requests
# ============================================================


class TestTransparentModeTokenRequests:
    """Tests for token requests in transparent mode."""

    @pytest.fixture
    def transparent_credentials(self):
        """Create test credentials for transparent mode."""
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            gateway_url="https://agw.example.com",
            integration_dependencies=[],
            certificate=None,
            private_key=None,
        )

    def test_system_token_uses_transparent_mode(self, transparent_credentials):
        """Request system token using transparent mode (no mTLS)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "transparent-system-token"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = get_system_token_mtls(transparent_credentials, timeout=60.0)

            assert result == "transparent-system-token"
            # Verify no SSL context was created (transparent mode)
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args.kwargs
            assert "verify" not in call_kwargs or call_kwargs["verify"] is not None

    def test_user_token_exchange_uses_transparent_mode(self, transparent_credentials):
        """Exchange user token using transparent mode (no mTLS)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "transparent-user-token"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = exchange_user_token(
                transparent_credentials, "user-jwt", timeout=60.0
            )

            assert result == "transparent-user-token"
            # Verify jwt-bearer grant was used
            call_args = mock_client.post.call_args
            data = call_args.kwargs.get("data", {})
            assert data["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
            assert data["assertion"] == "user-jwt"

    @pytest.fixture
    def mtls_credentials(self):
        """Create test credentials for STANDARD mode (with mTLS)."""
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            gateway_url="https://agw.example.com",
            integration_dependencies=[],
            certificate="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            private_key="-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
        )

    def test_system_token_uses_mtls_mode(self, mtls_credentials):
        """Request system token using STANDARD mode (with mTLS)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "mtls-system-token"}

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

            result = get_system_token_mtls(mtls_credentials, timeout=60.0)

            assert result == "mtls-system-token"
            # Verify SSL context was created (STANDARD mode)
            mock_ssl.assert_called_once()
