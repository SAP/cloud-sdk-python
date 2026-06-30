"""Unit tests for customer agent flow."""

import json
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from sap_cloud_sdk.agentgateway._customer import (
    detect_customer_agent_credentials,
    load_customer_credentials,
    get_system_token_mtls,
    exchange_user_token,
    get_mcp_tools_customer,
    _build_mcp_url,
    _resolve_dependency,
    _CREDENTIALS_PATH_ENV,
    _SERVICE_BINDING_ROOT_ENV,
    _BINDING_TYPE,
    _BINDING_TYPE_FILE,
    _CREDENTIALS_FILE,
    _DEFAULT_BINDING_ROOT,
)
from sap_cloud_sdk.agentgateway._mcp_session import invoke_mcp_tool as call_mcp_tool_customer
from sap_cloud_sdk.agentgateway._models import (
    CustomerCredentials,
    IntegrationDependency,
    MCPTool,
)
from sap_cloud_sdk.agentgateway._token_cache import _TokenCache
from sap_cloud_sdk.agentgateway.config import ClientConfig
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError, AgentGatewayServerError


# ============================================================
# Test: detect_customer_agent_credentials
# ============================================================


class TestDetectCustomerAgentCredentials:
    """Tests for customer agent credential detection."""

    def _make_binding(self, parent, name="my-binding"):
        """Create a servicebinding.io-compliant binding directory under parent."""
        binding_dir = parent / name
        binding_dir.mkdir(parents=True, exist_ok=True)
        (binding_dir / _BINDING_TYPE_FILE).write_text(_BINDING_TYPE)
        creds_file = binding_dir / _CREDENTIALS_FILE
        creds_file.write_text('{"clientid": "test"}')
        return creds_file

    def test_detect_from_env_var_path(self, tmp_path):
        """Detect credentials from path specified in environment variable."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text('{"clientid": "test"}')

        with patch.dict(os.environ, {_CREDENTIALS_PATH_ENV: str(creds_file)}):
            result = detect_customer_agent_credentials()
            assert result == str(creds_file)

    def test_detect_from_env_var_path_file_not_exists(self, tmp_path):
        """Return None when env var path doesn't exist."""
        env = {_CREDENTIALS_PATH_ENV: "/nonexistent/path", _SERVICE_BINDING_ROOT_ENV: str(tmp_path)}
        with patch.dict(os.environ, env, clear=False):
            result = detect_customer_agent_credentials()
            assert result is None

    def test_detect_from_service_binding_root(self, tmp_path):
        """Detect credentials by scanning SERVICE_BINDING_ROOT for a binding with matching type file."""
        creds_file = self._make_binding(tmp_path)

        env = {_SERVICE_BINDING_ROOT_ENV: str(tmp_path)}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop(_CREDENTIALS_PATH_ENV, None)
            result = detect_customer_agent_credentials()
            assert result == str(creds_file)

    def test_detect_from_default_path(self, tmp_path):
        """Detect credentials from default /bindings root when SERVICE_BINDING_ROOT is not set."""
        creds_file = self._make_binding(tmp_path)

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(_CREDENTIALS_PATH_ENV, None)
            os.environ.pop(_SERVICE_BINDING_ROOT_ENV, None)
            with patch("sap_cloud_sdk.agentgateway._customer._DEFAULT_BINDING_ROOT", str(tmp_path)):
                result = detect_customer_agent_credentials()
                assert result == str(creds_file)

    def test_skips_binding_with_wrong_type(self, tmp_path):
        """Ignore binding directories whose type file does not match."""
        wrong_dir = tmp_path / "other-binding"
        wrong_dir.mkdir()
        (wrong_dir / _BINDING_TYPE_FILE).write_text("something-else")
        (wrong_dir / _CREDENTIALS_FILE).write_text('{"clientid": "wrong"}')

        env = {_SERVICE_BINDING_ROOT_ENV: str(tmp_path)}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop(_CREDENTIALS_PATH_ENV, None)
            result = detect_customer_agent_credentials()
            assert result is None

    def test_service_binding_root_takes_priority_over_default(self, tmp_path):
        """SERVICE_BINDING_ROOT is checked before the hardcoded /bindings fallback."""
        sbr_dir = tmp_path / "sbr"
        sbr_dir.mkdir()
        creds_file = self._make_binding(sbr_dir)

        with patch.dict(os.environ, {_SERVICE_BINDING_ROOT_ENV: str(sbr_dir)}, clear=False):
            os.environ.pop(_CREDENTIALS_PATH_ENV, None)
            result = detect_customer_agent_credentials()
            assert result == str(creds_file)

    def test_no_credentials_returns_none(self, tmp_path):
        """Return None when no binding with matching type is found."""
        env = {_SERVICE_BINDING_ROOT_ENV: str(tmp_path)}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop(_CREDENTIALS_PATH_ENV, None)
            result = detect_customer_agent_credentials()
            assert result is None

    def test_env_var_takes_priority_over_service_binding_root(self, tmp_path):
        """AGW_CREDENTIALS_PATH env var takes priority over SERVICE_BINDING_ROOT."""
        creds_file = tmp_path / "custom_credentials.json"
        creds_file.write_text('{"clientid": "custom"}')

        sbr_dir = tmp_path / "sbr"
        sbr_dir.mkdir()
        self._make_binding(sbr_dir)

        env = {
            _CREDENTIALS_PATH_ENV: str(creds_file),
            _SERVICE_BINDING_ROOT_ENV: str(sbr_dir),
        }
        with patch.dict(os.environ, env, clear=False):
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

    def test_loads_nested_service_binding_integration_dependencies(self, tmp_path):
        """Load service binding integrationDependencies when tenant id is nested under data."""
        creds_file = tmp_path / "credentials.json"
        creds_data = {
            "tokenServiceUrl": "https://ias.example.com/oauth2/token",
            "clientid": "my-client-id",
            "certificate": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "privateKey": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "gatewayUrl": "https://agw.example.com",
            "integrationDependencies": [
                {
                    "ordId": "sap.s4:apiResource:CE_COSTCENTER_0001_MCP:v1",
                    "data": {
                        "globalTenantId": "731473562",
                    },
                },
            ],
        }
        creds_file.write_text(json.dumps(creds_data))

        result = load_customer_credentials(str(creds_file))

        assert len(result.integration_dependencies) == 1
        assert (
            result.integration_dependencies[0].ord_id
            == "sap.s4:apiResource:CE_COSTCENTER_0001_MCP:v1"
        )
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
                {"ordId": "missing-global-tenant-id-field"},  # Missing 'globalTenantId' key
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
# Test: _resolve_dependency
# ============================================================


class TestResolveDependency:
    """Tests for ORD ID → tenant ID resolution."""

    def _make_credentials(self, deps):
        return CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="cert",
            private_key="key",
            gateway_url="https://agw.example.com",
            integration_dependencies=deps,
        )

    def test_resolves_matching_ord_id(self):
        """Return the dependency whose ord_id matches."""
        dep = IntegrationDependency(ord_id="sap.s4:apiResource:FOO:v1", global_tenant_id="111")
        creds = self._make_credentials([dep])
        assert _resolve_dependency(creds, "sap.s4:apiResource:FOO:v1") is dep

    def test_raises_when_not_found(self):
        """Raise error when the ORD ID is not in the list."""
        creds = self._make_credentials([
            IntegrationDependency(ord_id="sap.s4:apiResource:FOO:v1", global_tenant_id="111"),
        ])
        with pytest.raises(AgentGatewaySDKError, match="not found in integrationDependencies"):
            _resolve_dependency(creds, "sap.s4:apiResource:BAR:v1")

    def test_raises_on_multiple_matches(self):
        """Raise error when the same ORD ID appears with different tenant IDs."""
        creds = self._make_credentials([
            IntegrationDependency(ord_id="sap.s4:apiResource:FOO:v1", global_tenant_id="111"),
            IntegrationDependency(ord_id="sap.s4:apiResource:FOO:v1", global_tenant_id="222"),
        ])
        with pytest.raises(AgentGatewaySDKError, match="matches multiple integrationDependencies"):
            _resolve_dependency(creds, "sap.s4:apiResource:FOO:v1")

    def test_raises_with_empty_dependencies(self):
        """Raise error when integrationDependencies is empty."""
        creds = self._make_credentials([])
        with pytest.raises(AgentGatewaySDKError, match="not found in integrationDependencies"):
            _resolve_dependency(creds, "sap.s4:apiResource:FOO:v1")


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

    @pytest.mark.asyncio
    async def test_filters_to_single_server_when_ord_id_given(self):
        """Only query the server whose ord_id matches when ord_id is provided."""
        credentials = CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="cert",
            private_key="key",
            gateway_url="https://agw.example.com",
            integration_dependencies=[
                IntegrationDependency(ord_id="sap.s4:apiResource:FOO:v1", global_tenant_id="111"),
                IntegrationDependency(ord_id="sap.s4:apiResource:BAR:v1", global_tenant_id="222"),
            ],
        )
        mock_tool = MCPTool(
            name="foo_tool", server_name="FOO", description="", input_schema={},
            url="https://agw.example.com/v1/mcp/sap.s4:apiResource:FOO:v1/111",
        )

        with patch(
            "sap_cloud_sdk.agentgateway._customer._list_server_tools",
            new_callable=AsyncMock,
            return_value=[mock_tool],
        ) as mock_list:
            result = await get_mcp_tools_customer(
                credentials, "token", 60.0, ord_id="sap.s4:apiResource:FOO:v1"
            )

        assert len(result) == 1
        assert result[0].name == "foo_tool"
        assert mock_list.call_count == 1
        called_url = mock_list.call_args[0][0]
        assert "FOO" in called_url and "111" in called_url

    @pytest.mark.asyncio
    async def test_raises_when_ord_id_not_found(self):
        """Raise error when the given ord_id is not in integrationDependencies."""
        credentials = CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="cert",
            private_key="key",
            gateway_url="https://agw.example.com",
            integration_dependencies=[
                IntegrationDependency(ord_id="sap.s4:apiResource:FOO:v1", global_tenant_id="111"),
            ],
        )
        with pytest.raises(AgentGatewaySDKError, match="not found in integrationDependencies"):
            await get_mcp_tools_customer(
                credentials, "token", 60.0, ord_id="sap.s4:apiResource:MISSING:v1"
            )

    @pytest.mark.asyncio
    async def test_raises_when_ord_id_matches_multiple(self):
        """Raise error when the given ord_id matches multiple entries."""
        credentials = CustomerCredentials(
            token_service_url="https://ias.example.com/oauth2/token",
            client_id="test-client",
            certificate="cert",
            private_key="key",
            gateway_url="https://agw.example.com",
            integration_dependencies=[
                IntegrationDependency(ord_id="sap.s4:apiResource:FOO:v1", global_tenant_id="111"),
                IntegrationDependency(ord_id="sap.s4:apiResource:FOO:v1", global_tenant_id="222"),
            ],
        )
        with pytest.raises(AgentGatewaySDKError, match="matches multiple integrationDependencies"):
            await get_mcp_tools_customer(
                credentials, "token", 60.0, ord_id="sap.s4:apiResource:FOO:v1"
            )


# ============================================================
# Test: invoke_mcp_tool (via customer flow)
# ============================================================


class TestInvokeMcpTool:
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
                "sap_cloud_sdk.agentgateway._mcp_session.httpx.AsyncClient",
            ) as mock_client_class,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.streamable_http_client",
            ) as mock_stream,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.ClientSession",
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
            mock_result.isError = False
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
                "sap_cloud_sdk.agentgateway._mcp_session.httpx.AsyncClient",
            ) as mock_client_class,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.streamable_http_client",
            ) as mock_stream,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.ClientSession",
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
            mock_result.isError = False
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

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_result_is_none(self, mock_tool):
        """Return empty string when call_tool returns None (null MCP response)."""
        with (
            patch("sap_cloud_sdk.agentgateway._mcp_session.httpx.AsyncClient") as mock_client_class,
            patch("sap_cloud_sdk.agentgateway._mcp_session.streamable_http_client") as mock_stream,
            patch("sap_cloud_sdk.agentgateway._mcp_session.ClientSession") as mock_session_class,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_stream_ctx = AsyncMock()
            mock_stream_ctx.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock(), None))
            mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_stream.return_value = mock_stream_ctx

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock()
            mock_session.call_tool = AsyncMock(return_value=None)
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_ctx

            result = await call_mcp_tool_customer(mock_tool, "auth-token", 60.0)
            assert result == ""

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_exception_group_contains_only_attr_error(self, mock_tool):
        """Return empty string when anyio wraps an AttributeError (older MCP null-result bug) in an ExceptionGroup."""
        with (
            patch("sap_cloud_sdk.agentgateway._mcp_session.httpx.AsyncClient") as mock_client_class,
            patch("sap_cloud_sdk.agentgateway._mcp_session.streamable_http_client") as mock_stream,
            patch("sap_cloud_sdk.agentgateway._mcp_session.ClientSession") as mock_session_class,
        ):
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Simulate anyio wrapping the AttributeError in a BaseExceptionGroup
            nested = BaseExceptionGroup(
                "unhandled errors in a TaskGroup",
                [BaseExceptionGroup(
                    "unhandled errors in a TaskGroup",
                    [AttributeError("'NoneType' object has no attribute 'isError'")],
                )],
            )
            mock_stream_ctx = AsyncMock()
            mock_stream_ctx.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock(), None))
            mock_stream_ctx.__aexit__ = AsyncMock(side_effect=nested)
            mock_stream.return_value = mock_stream_ctx

            mock_session_class.return_value = AsyncMock()

            result = await call_mcp_tool_customer(mock_tool, "auth-token", 60.0)
            assert result == ""

    @pytest.mark.asyncio
    async def test_raises_server_error_when_result_is_error(self, mock_tool):
        """Raise AgentGatewayServerError when tool result has isError=True."""
        with (
            patch("sap_cloud_sdk.agentgateway._mcp_session.httpx.AsyncClient") as mock_client_class,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.streamable_http_client"
            ) as mock_stream,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.ClientSession"
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
            mock_result.isError = True
            error_content = MagicMock()
            error_content.text = "Internal tool error"
            mock_result.content = [error_content]
            mock_session.call_tool = AsyncMock(return_value=mock_result)
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_ctx

            with pytest.raises(AgentGatewayServerError, match="Internal tool error"):
                await call_mcp_tool_customer(mock_tool, "auth-token", 60.0)

    @pytest.mark.asyncio
    async def test_raises_server_error_on_mcp_error_during_call(self, mock_tool):
        """Raise AgentGatewayServerError when MCP call_tool raises McpError."""
        from mcp import McpError
        from mcp.types import ErrorData

        with (
            patch("sap_cloud_sdk.agentgateway._mcp_session.httpx.AsyncClient") as mock_client_class,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.streamable_http_client"
            ) as mock_stream,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.ClientSession"
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
            mock_session.call_tool = AsyncMock(
                side_effect=McpError(
                    ErrorData(
                        code=-32600,
                        message="MCP server card for ORD ID sap.mcpbuilder:apiResource:API_SALES_ORDE_SRV_MCP_1:v1 not found in registry",
                    )
                )
            )
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_ctx

            with pytest.raises(
                AgentGatewayServerError,
                match="not found in registry",
            ) as exc_info:
                await call_mcp_tool_customer(mock_tool, "auth-token", 60.0)

            assert exc_info.value.error_code == -32600

    @pytest.mark.asyncio
    async def test_raises_server_error_on_mcp_error_during_initialize(self, mock_tool):
        """Raise AgentGatewayServerError when MCP initialize raises McpError."""
        from mcp import McpError
        from mcp.types import ErrorData

        with (
            patch("sap_cloud_sdk.agentgateway._mcp_session.httpx.AsyncClient") as mock_client_class,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.streamable_http_client"
            ) as mock_stream,
            patch(
                "sap_cloud_sdk.agentgateway._mcp_session.ClientSession"
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
            mock_session.initialize = AsyncMock(
                side_effect=McpError(ErrorData(code=-32600, message="Unauthorized"))
            )
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session_ctx

            with pytest.raises(
                AgentGatewayServerError,
                match="rejected MCP session.*Unauthorized",
            ):
                await call_mcp_tool_customer(mock_tool, "auth-token", 60.0)
