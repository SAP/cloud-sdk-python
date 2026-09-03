"""Unit tests for DestinationClient operations and behaviors."""

import pytest
from unittest.mock import Mock, patch
from requests import Response

from sap_cloud_sdk.destination.client import DestinationClient
from sap_cloud_sdk.core._http_client import HttpMethod
from sap_cloud_sdk.destination._models import (
    Destination,
    Label,
    Level,
    AccessStrategy,
    ConsumptionLevel,
    DestinationType,
    ListOptions,
    PatchLabels,
    TransparentProxy,
    TransparentProxyDestination,
    ConsumptionOptions,
)
from sap_cloud_sdk.destination.utils._pagination import PagedResult
from sap_cloud_sdk.destination.exceptions import (
    DestinationOperationError,
    HttpError,
)


def _make_response(status=200, json_data=None, text="", headers=None):
    resp = Mock(spec=Response)
    resp.status_code = status
    resp.text = text
    resp.headers = headers or {}
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


def _make_simple_resp(mock_http):
    """Configure mock_http with a minimal valid v2 get_destination response."""
    mock_http.request.return_value = _make_response(200, json_data={
        "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
        "authTokens": [],
        "certificates": [],
    })


@pytest.fixture
def mock_http():
    http = Mock()
    http.request.return_value = _make_response(200)
    return http


@pytest.fixture
def destination_client(mock_http):
    return DestinationClient(mock_http)


class TestDestinationClientReadOperations:

    def test_get_instance_destination_success(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data={"name": "my-dest", "type": "HTTP"})
        dest = destination_client.get_instance_destination("my-dest")
        assert isinstance(dest, Destination)
        assert dest.name == "my-dest"
        assert dest.type == DestinationType.HTTP
        args, kwargs = mock_http.request.call_args
        assert "instanceDestinations/my-dest" in args[1]
        assert kwargs.get("tenant_subdomain") is None

    def test_get_instance_destination_not_found_returns_none(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        result = destination_client.get_instance_destination("unknown")
        assert result is None

    def test_get_instance_destination_http_error_wrapped(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(500, text="err")
        with pytest.raises(DestinationOperationError, match="failed to get destination 'my-dest'"):
            destination_client.get_instance_destination("my-dest")

    def test_get_subaccount_destination_requires_tenant_for_subscriber_access(self):
        client = DestinationClient(Mock())
        for strat in [AccessStrategy.SUBSCRIBER_ONLY, AccessStrategy.SUBSCRIBER_FIRST, AccessStrategy.PROVIDER_FIRST]:
            with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
                client.get_subaccount_destination("my-dest", access_strategy=strat, tenant=None)

    def test_get_subaccount_destination_provider_only_no_tenant_required(self):
        client = DestinationClient(Mock())
        dest = Destination(name="prov-dest", type="HTTP")
        with patch.object(client, "_get_destination", return_value=dest) as mock_get:
            result = client.get_subaccount_destination("prov-dest", access_strategy=AccessStrategy.PROVIDER_ONLY, tenant=None)
            assert result is dest
            mock_get.assert_called_once()
            called_kwargs = mock_get.call_args.kwargs
            assert called_kwargs.get("tenant_subdomain") is None

    def test_get_subaccount_destination_subscriber_first_fallback_to_provider(self):
        client = DestinationClient(Mock())
        dest = Destination(name="my-dest", type="HTTP")
        with patch.object(client, "_get_destination", side_effect=[None, dest]) as mock_get:
            result = client.get_subaccount_destination("my-dest", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-1")
            assert result is dest
            assert mock_get.call_count == 2

    def test_get_subaccount_destination_provider_first_fallback_to_subscriber(self):
        client = DestinationClient(Mock())
        dest = Destination(name="my-dest", type="HTTP")
        with patch.object(client, "_get_destination", side_effect=[None, dest]) as mock_get:
            result = client.get_subaccount_destination("my-dest", access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="tenant-1")
            assert result is dest
            assert mock_get.call_count == 2

    def test_get_subaccount_destination_http_error_wrapped(self):
        client = DestinationClient(Mock())
        with patch.object(client, "_get_destination", side_effect=HttpError("bad", status_code=500)):
            with pytest.raises(DestinationOperationError, match="failed to get destination 'name'"):
                client.get_subaccount_destination("name", access_strategy=AccessStrategy.PROVIDER_ONLY)

    def test_get_destination_success(self, mock_http, destination_client):
        """Test successful destination consumption."""
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
            "authTokens": [
                {
                    "type": "Bearer",
                    "value": "dG9rZW4xMjM=",
                    "http_header": {"key": "Authorization", "value": "Bearer token123"},
                }
            ],
            "certificates": [],
        })
        result = destination_client.get_destination("my-api")
        assert isinstance(result, Destination)
        assert result.name == "my-api"
        assert result.url == "https://api.example.com"
        assert len(result.auth_tokens) == 1
        assert result.auth_tokens[0].type == "Bearer"
        assert result.auth_tokens[0].http_header["key"] == "Authorization"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v2/destinations/my-api"
        assert kwargs.get("tenant_subdomain") is None
        assert kwargs.get("headers") == {"Accept": "application/json"}

    def test_get_destination_with_fragment_name(self, mock_http, destination_client):
        """Test consumption with fragment merging."""
        _make_simple_resp(mock_http)
        result = destination_client.get_destination("my-api", options=ConsumptionOptions(fragment_name="production"))
        assert result is not None
        args, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-fragment-name"] == "production"

    def test_get_destination_with_tenant_context(self, mock_http, destination_client):
        """Test consumption with tenant context for user token exchange."""
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
            "authTokens": [
                {
                    "type": "Bearer",
                    "value": "dXNlcnRva2Vu",
                    "http_header": {"key": "Authorization", "value": "Bearer usertoken"},
                    "scope": "read write",
                }
            ],
            "certificates": [],
        })
        result = destination_client.get_destination("my-api", options=ConsumptionOptions(tenant="tenant-1"))
        assert isinstance(result, Destination)
        assert len(result.auth_tokens) == 1
        assert result.auth_tokens[0].scope == "read write"
        args, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-tenant"] == "tenant-1"

    def test_get_destination_with_fragment_and_tenant(self, mock_http, destination_client):
        """Test consumption with both fragment and tenant."""
        _make_simple_resp(mock_http)
        result = destination_client.get_destination("my-api", options=ConsumptionOptions(fragment_name="prod", tenant="tenant-1"))
        assert result is not None
        args, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-fragment-name"] == "prod"
        assert kwargs["headers"]["X-tenant"] == "tenant-1"

    def test_get_destination_not_found_returns_none(self, mock_http, destination_client):
        """Test consumption returns None when destination not found."""
        mock_http.request.return_value = _make_response(404, text="Not Found")
        assert destination_client.get_destination("unknown") is None

    def test_get_destination_http_error_wrapped(self, mock_http, destination_client):
        """Test non-404 HTTP errors are wrapped."""
        mock_http.request.return_value = _make_response(500, text="Internal Error")
        with pytest.raises(DestinationOperationError, match="failed to consume destination 'my-api'"):
            destination_client.get_destination("my-api")

    def test_get_destination_invalid_json_wrapped(self, mock_http, destination_client):
        """Test invalid JSON response is wrapped."""
        resp = _make_response(200)
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_http.request.return_value = resp
        with pytest.raises(DestinationOperationError, match="failed to parse consume destination response"):
            destination_client.get_destination("my-api")

    def test_get_destination_missing_destination_configuration(self, mock_http, destination_client):
        """Test response missing destinationConfiguration field."""
        mock_http.request.return_value = _make_response(200, json_data={"authTokens": [], "certificates": []})
        with pytest.raises(DestinationOperationError, match="failed to parse consume destination response"):
            destination_client.get_destination("my-api")

    def test_get_destination_with_multiple_auth_tokens(self, mock_http, destination_client):
        """Test consumption with multiple auth tokens."""
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
            "authTokens": [
                {"type": "Bearer", "value": "dG9rZW4x", "http_header": {"key": "Authorization", "value": "Bearer token1"}},
                {"type": "ApiKey", "value": "YXBpa2V5", "http_header": {"key": "X-API-Key", "value": "apikey123"}},
            ],
            "certificates": [],
        })
        result = destination_client.get_destination("my-api")
        assert isinstance(result, Destination)
        assert len(result.auth_tokens) == 2
        assert result.auth_tokens[0].type == "Bearer"
        assert result.auth_tokens[1].type == "ApiKey"

    def test_get_destination_with_certificates(self, mock_http, destination_client):
        """Test consumption returns certificates."""
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
            "authTokens": [],
            "certificates": [{"Name": "client-cert", "Content": "Y2VydGNvbnRlbnQ=", "Type": "PEM"}],
        })
        result = destination_client.get_destination("my-api")
        assert isinstance(result, Destination)
        assert len(result.certificates) == 1
        assert result.certificates[0].name == "client-cert"
        assert result.certificates[0].type == "PEM"

    def test_get_destination_with_refresh_token(self, mock_http, destination_client):
        """Test auth token includes refresh token."""
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
            "authTokens": [
                {
                    "type": "Bearer",
                    "value": "dG9rZW4=",
                    "http_header": {"key": "Authorization", "value": "Bearer token"},
                    "refresh_token": "cmVmcmVzaA==",
                    "scope": "openid profile",
                }
            ],
            "certificates": [],
        })
        result = destination_client.get_destination("my-api")
        assert isinstance(result, Destination)
        assert result.auth_tokens[0].refresh_token == "cmVmcmVzaA=="
        assert result.auth_tokens[0].scope == "openid profile"

    def test_get_destination_with_level_instance(self, mock_http, destination_client):
        """Test get_destination with level=INSTANCE uses @instance in path."""
        _make_simple_resp(mock_http)
        result = destination_client.get_destination("my-api", level=ConsumptionLevel.INSTANCE)
        assert result is not None
        assert result.name == "my-api"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v2/destinations/my-api@instance"

    def test_get_destination_with_level_subaccount(self, mock_http, destination_client):
        """Test get_destination with level=SUBACCOUNT uses @subaccount in path."""
        _make_simple_resp(mock_http)
        result = destination_client.get_destination("my-api", level=ConsumptionLevel.SUBACCOUNT)
        assert result is not None
        assert result.name == "my-api"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v2/destinations/my-api@subaccount"

    def test_get_destination_with_level_and_options(self, mock_http, destination_client):
        """Test get_destination combining level parameter with ConsumptionOptions."""
        _make_simple_resp(mock_http)
        options = ConsumptionOptions(fragment_name="production", tenant="tenant-1")
        result = destination_client.get_destination("my-api", level=ConsumptionLevel.SUBACCOUNT, options=options)
        assert result is not None
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v2/destinations/my-api@subaccount"
        assert kwargs["headers"]["X-fragment-name"] == "production"
        assert kwargs["headers"]["X-tenant"] == "tenant-1"

    def test_get_destination_with_level_provider_subaccount(self, mock_http, destination_client):
        """Test get_destination with level=PROVIDER_SUBACCOUNT uses @provider_subaccount in path."""
        _make_simple_resp(mock_http)
        result = destination_client.get_destination("my-api", level=ConsumptionLevel.PROVIDER_SUBACCOUNT)
        assert result is not None
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v2/destinations/my-api@provider_subaccount"

    def test_get_destination_with_level_provider_instance(self, mock_http, destination_client):
        """Test get_destination with level=PROVIDER_INSTANCE uses @provider_instance in path."""
        _make_simple_resp(mock_http)
        result = destination_client.get_destination("my-api", level=ConsumptionLevel.PROVIDER_INSTANCE)
        assert result is not None
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v2/destinations/my-api@provider_instance"

    def test_get_destination_with_fragment_level(self, mock_http, destination_client):
        """Test that fragment_level appends @level to X-fragment-name header."""
        _make_simple_resp(mock_http)
        options = ConsumptionOptions(fragment_name="my-frag", fragment_level=ConsumptionLevel.PROVIDER_SUBACCOUNT)
        destination_client.get_destination("my-api", options=options)
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-fragment-name"] == "my-frag@provider_subaccount"

    def test_get_destination_with_fragment_name_and_level_combined(self, mock_http, destination_client):
        """Test fragment_name and fragment_level combine correctly into the header."""
        _make_simple_resp(mock_http)
        options = ConsumptionOptions(fragment_name="prod-frag", fragment_level=ConsumptionLevel.INSTANCE)
        destination_client.get_destination("my-api", options=options)
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-fragment-name"] == "prod-frag@instance"

    def test_get_destination_fragment_level_without_fragment_name_has_no_effect(self, mock_http, destination_client):
        """Test that fragment_level alone (no fragment_name) does not add X-fragment-name header."""
        _make_simple_resp(mock_http)
        options = ConsumptionOptions(fragment_level=ConsumptionLevel.PROVIDER_INSTANCE)
        destination_client.get_destination("my-api", options=options)
        _, kwargs = mock_http.request.call_args
        assert "X-fragment-name" not in kwargs["headers"]

    def test_get_destination_empty_auth_tokens_and_certificates(self, mock_http, destination_client):
        """Test consumption with no auth tokens or certificates."""
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {
                "name": "my-api", "type": "HTTP", "url": "https://api.example.com", "authentication": "NoAuthentication",
            },
            "authTokens": [],
            "certificates": [],
        })
        result = destination_client.get_destination("my-api")
        assert isinstance(result, Destination)
        assert len(result.auth_tokens) == 0
        assert len(result.certificates) == 0

    def test_get_destination_with_fragment_optional_true(self, mock_http, destination_client):
        """X-fragment-optional: true is sent when fragment_optional=True."""
        _make_simple_resp(mock_http)
        destination_client.get_destination("my-api", options=ConsumptionOptions(fragment_name="prod", fragment_optional=True))
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-fragment-optional"] == "true"

    def test_get_destination_with_fragment_optional_false(self, mock_http, destination_client):
        """X-fragment-optional: false is sent when fragment_optional=False."""
        _make_simple_resp(mock_http)
        destination_client.get_destination("my-api", options=ConsumptionOptions(fragment_name="prod", fragment_optional=False))
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-fragment-optional"] == "false"

    def test_get_destination_fragment_optional_not_sent_when_none(self, mock_http, destination_client):
        """X-fragment-optional header is omitted when fragment_optional is not set."""
        _make_simple_resp(mock_http)
        destination_client.get_destination("my-api", options=ConsumptionOptions(fragment_name="prod"))
        _, kwargs = mock_http.request.call_args
        assert "X-fragment-optional" not in kwargs["headers"]

    def test_get_destination_with_user_token(self, mock_http, destination_client):
        """X-user-token header is sent for OAuth2UserTokenExchange flows."""
        _make_simple_resp(mock_http)
        destination_client.get_destination("my-api", options=ConsumptionOptions(user_token="my.jwt.token"))
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-user-token"] == "my.jwt.token"

    def test_get_destination_with_subject_token_and_type(self, mock_http, destination_client):
        """X-subject-token and X-subject-token-type are sent for OAuth2TokenExchange."""
        _make_simple_resp(mock_http)
        destination_client.get_destination(
            "my-api",
            options=ConsumptionOptions(
                subject_token="subj-token",
                subject_token_type="urn:ietf:params:oauth:token-type:access_token",
            ),
        )
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-subject-token"] == "subj-token"
        assert kwargs["headers"]["X-subject-token-type"] == "urn:ietf:params:oauth:token-type:access_token"

    def test_get_destination_with_actor_token_and_type(self, mock_http, destination_client):
        """X-actor-token and X-actor-token-type are sent for OAuth2TokenExchange."""
        _make_simple_resp(mock_http)
        destination_client.get_destination(
            "my-api",
            options=ConsumptionOptions(
                actor_token="actor-token",
                actor_token_type="urn:ietf:params:oauth:token-type:access_token",
            ),
        )
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-actor-token"] == "actor-token"
        assert kwargs["headers"]["X-actor-token-type"] == "urn:ietf:params:oauth:token-type:access_token"

    def test_get_destination_with_saml_assertion(self, mock_http, destination_client):
        """X-samlAssertion is sent for OAuth2SAMLBearerAssertion with ClientProvided."""
        _make_simple_resp(mock_http)
        destination_client.get_destination("my-api", options=ConsumptionOptions(saml_assertion="base64saml=="))
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-samlAssertion"] == "base64saml=="

    def test_get_destination_with_refresh_token_option(self, mock_http, destination_client):
        """X-refresh-token is sent for OAuth2RefreshToken destinations."""
        _make_simple_resp(mock_http)
        destination_client.get_destination("my-api", options=ConsumptionOptions(refresh_token="my-refresh-token"))
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-refresh-token"] == "my-refresh-token"

    def test_get_destination_with_code(self, mock_http, destination_client):
        """X-code is sent for OAuth2AuthorizationCode destinations."""
        _make_simple_resp(mock_http)
        destination_client.get_destination("my-api", options=ConsumptionOptions(code="auth-code-123"))
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-code"] == "auth-code-123"

    def test_get_destination_with_redirect_uri(self, mock_http, destination_client):
        """X-redirect-uri is sent for OAuth2AuthorizationCode destinations."""
        _make_simple_resp(mock_http)
        destination_client.get_destination(
            "my-api",
            options=ConsumptionOptions(code="auth-code-123", redirect_uri="https://app/callback"),
        )
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-redirect-uri"] == "https://app/callback"

    def test_get_destination_with_code_verifier(self, mock_http, destination_client):
        """X-code-verifier is sent for PKCE-enabled OAuth2AuthorizationCode destinations."""
        _make_simple_resp(mock_http)
        destination_client.get_destination(
            "my-api",
            options=ConsumptionOptions(code="auth-code-123", code_verifier="pkce-verifier-abc"),
        )
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-code-verifier"] == "pkce-verifier-abc"

    def test_get_destination_with_chain_name(self, mock_http, destination_client):
        """X-chain-name is sent when chain_name is provided."""
        _make_simple_resp(mock_http)
        destination_client.get_destination("my-api", options=ConsumptionOptions(chain_name="my-chain"))
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-chain-name"] == "my-chain"

    def test_get_destination_with_chain_vars(self, mock_http, destination_client):
        """X-chain-var-<name> headers are sent for each chain variable."""
        _make_simple_resp(mock_http)
        destination_client.get_destination(
            "my-api",
            options=ConsumptionOptions(
                chain_name="my-chain",
                chain_vars={"subject_token": "tok123", "subject_token_type": "access_token"},
            ),
        )
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-chain-name"] == "my-chain"
        assert kwargs["headers"]["X-chain-var-subject_token"] == "tok123"
        assert kwargs["headers"]["X-chain-var-subject_token_type"] == "access_token"

    def test_get_destination_chain_vars_without_chain_name(self, mock_http, destination_client):
        """chain_vars without chain_name: headers are still forwarded (API enforces pairing)."""
        _make_simple_resp(mock_http)
        destination_client.get_destination(
            "my-api",
            options=ConsumptionOptions(chain_vars={"subject_token": "tok"}),
        )
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-chain-var-subject_token"] == "tok"
        assert "X-chain-name" not in kwargs["headers"]

    def test_get_destination_all_headers_combined(self, mock_http, destination_client):
        """Multiple unrelated headers can be sent simultaneously."""
        _make_simple_resp(mock_http)
        destination_client.get_destination(
            "my-api",
            options=ConsumptionOptions(
                fragment_name="prod",
                fragment_optional=True,
                tenant="tenant-1",
                user_token="user.jwt",
            ),
        )
        _, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-fragment-name"] == "prod"
        assert kwargs["headers"]["X-fragment-optional"] == "true"
        assert kwargs["headers"]["X-tenant"] == "tenant-1"
        assert kwargs["headers"]["X-user-token"] == "user.jwt"

    # --- Transparent proxy tests ---

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_instance_destination_with_proxy_enabled(self, mock_load_proxy, mock_http):
        """Test get_instance_destination with proxy_enabled=True returns TransparentProxyDestination."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_instance_destination("my-dest", proxy_enabled=True)
        assert isinstance(result, TransparentProxyDestination)
        assert result.name == "my-dest"
        assert result.url == "http://test-proxy.test-ns"
        assert result.headers == {"X-destination-name": "my-dest"}
        mock_http.request.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_instance_destination_with_proxy_disabled(self, mock_load_proxy, mock_http):
        """Test get_instance_destination with proxy_enabled=False uses normal HTTP flow."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_http.request.return_value = _make_response(200, json_data={"name": "my-dest", "type": "HTTP"})
        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_instance_destination("my-dest", proxy_enabled=False)
        assert isinstance(result, Destination)
        assert result.name == "my-dest"
        mock_http.request.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_subaccount_destination_with_proxy_enabled(self, mock_load_proxy, mock_http):
        """Test get_subaccount_destination with proxy_enabled=True returns TransparentProxyDestination."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_subaccount_destination(
            "my-dest", access_strategy=AccessStrategy.PROVIDER_ONLY, proxy_enabled=True
        )
        assert isinstance(result, TransparentProxyDestination)
        assert result.name == "my-dest"
        assert result.url == "http://test-proxy.test-ns"
        assert result.headers == {"X-destination-name": "my-dest"}
        mock_http.request.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_subaccount_destination_with_proxy_disabled(self, mock_load_proxy, mock_http):
        """Test get_subaccount_destination with proxy_enabled=False uses normal HTTP flow."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        client = DestinationClient(mock_http, use_default_proxy=True)
        dest = Destination(name="my-dest", type="HTTP")
        with patch.object(client, "_get_destination", return_value=dest) as mock_get:
            result = client.get_subaccount_destination(
                "my-dest", access_strategy=AccessStrategy.PROVIDER_ONLY, proxy_enabled=False
            )
            assert isinstance(result, Destination)
            assert result.name == "my-dest"
            mock_get.assert_called_once()

    def test_get_subaccount_destination_proxy_enabled_no_proxy_configured_uses_normal_flow(self, mock_http):
        client = DestinationClient(mock_http, use_default_proxy=False)
        dest = Destination(name="my-dest", type="HTTP")
        with patch.object(client, "_get_destination", return_value=dest) as mock_get:
            result = client.get_subaccount_destination(
                "my-dest", access_strategy=AccessStrategy.PROVIDER_ONLY, proxy_enabled=True
            )
            assert isinstance(result, Destination)
            mock_get.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_subaccount_destination_proxy_with_subscriber_strategy(self, mock_load_proxy, mock_http):
        """Test get_subaccount_destination with proxy_enabled and SUBSCRIBER_FIRST strategy."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_subaccount_destination(
            "my-dest", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant", proxy_enabled=True
        )
        assert isinstance(result, TransparentProxyDestination)
        assert result.name == "my-dest"
        mock_http.request.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_client_initialization_loads_proxy(self, mock_load_proxy, mock_http):
        """Test that DestinationClient initialization calls load_transparent_proxy."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy
        client = DestinationClient(mock_http, use_default_proxy=True)
        mock_load_proxy.assert_called_once()
        assert client._transparent_proxy == proxy

    def test_client_initialization_no_proxy(self, mock_http):
        """Test that DestinationClient initialization handles no proxy configuration."""
        client = DestinationClient(mock_http, use_default_proxy=False)
        assert client._transparent_proxy is None

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_transparent_proxy_destination_url_format(self, mock_load_proxy, mock_http):
        """Test that TransparentProxyDestination generates correct URL format."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="my-proxy", namespace="my-namespace")
        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_instance_destination("test-destination", proxy_enabled=True)
        assert isinstance(result, TransparentProxyDestination)
        assert result.url == "http://my-proxy.my-namespace"
        assert result.headers == {"X-destination-name": "test-destination"}

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_transparent_proxy_destination_headers_format(self, mock_load_proxy, mock_http):
        """Test that TransparentProxyDestination generates correct headers."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        client = DestinationClient(mock_http, use_default_proxy=True)
        destination_name = "complex-destination-name-123"
        result = client.get_instance_destination(destination_name, proxy_enabled=True)
        assert isinstance(result, TransparentProxyDestination)
        assert result.headers["X-destination-name"] == destination_name

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_instance_destination_default_proxy_disabled(self, mock_load_proxy, mock_http):
        """Test that proxy_enabled defaults to client's use_default_proxy for get_instance_destination."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_http.request.return_value = _make_response(200, json_data={"name": "my-dest", "type": "HTTP"})
        client = DestinationClient(mock_http, use_default_proxy=False)
        result = client.get_instance_destination("my-dest")
        assert isinstance(result, Destination)
        mock_http.request.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_subaccount_destination_default_proxy_disabled(self, mock_load_proxy, mock_http):
        """Test that proxy_enabled defaults to client's use_default_proxy for get_subaccount_destination."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        client = DestinationClient(mock_http, use_default_proxy=False)
        dest = Destination(name="my-dest", type="HTTP")
        with patch.object(client, "_get_destination", return_value=dest) as mock_get:
            result = client.get_subaccount_destination("my-dest", access_strategy=AccessStrategy.PROVIDER_ONLY)
            assert isinstance(result, Destination)
            mock_get.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_with_proxy_enabled(self, mock_load_proxy, mock_http):
        """Test get_destination (v2 API) with proxy_enabled=True returns TransparentProxyDestination."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_destination("my-api", proxy_enabled=True)
        assert isinstance(result, TransparentProxyDestination)
        assert result.name == "my-api"
        assert result.url == "http://test-proxy.test-ns"
        assert result.headers == {"X-destination-name": "my-api"}
        mock_http.request.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_with_proxy_disabled(self, mock_load_proxy, mock_http):
        """Test get_destination (v2 API) with proxy_enabled=False uses normal HTTP flow."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
            "authTokens": [],
            "certificates": [],
        })
        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_destination("my-api", proxy_enabled=False)
        assert isinstance(result, Destination)
        assert result.name == "my-api"
        assert result.url == "https://api.example.com"
        mock_http.request.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_with_options_and_proxy_disabled(self, mock_load_proxy, mock_http):
        """Test get_destination with ConsumptionOptions and proxy disabled."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
            "authTokens": [],
            "certificates": [],
        })
        client = DestinationClient(mock_http, use_default_proxy=False)
        result = client.get_destination("my-api", options=ConsumptionOptions(fragment_name="prod", tenant="tenant-1"), proxy_enabled=False)
        assert isinstance(result, Destination)
        args, kwargs = mock_http.request.call_args
        assert kwargs["headers"]["X-fragment-name"] == "prod"
        assert kwargs["headers"]["X-tenant"] == "tenant-1"

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_default_proxy_enabled(self, mock_load_proxy, mock_http):
        """Test that proxy_enabled defaults to client's use_default_proxy for get_destination."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_destination("my-api")
        assert isinstance(result, TransparentProxyDestination)
        mock_http.request.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_default_proxy_disabled(self, mock_load_proxy, mock_http):
        """Test that get_destination uses normal flow when proxy is disabled by default."""
        mock_load_proxy.return_value = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
            "authTokens": [],
            "certificates": [],
        })
        client = DestinationClient(mock_http, use_default_proxy=False)
        result = client.get_destination("my-api")
        assert isinstance(result, Destination)
        mock_http.request.assert_called_once()

    def test_get_destination_skip_token_retrieval_sends_query_param(self, mock_http, destination_client):
        """Test that skip_token_retrieval=True sends $skipTokenRetrieval=true query param."""
        mock_http.request.return_value = _make_response(200, json_data={
            "destinationConfiguration": {
                "name": "my-api", "type": "HTTP", "url": "https://api.example.com", "clientId": "my-client-id",
            },
            "authTokens": [],
            "certificates": [],
        })
        result = destination_client.get_destination("my-api", options=ConsumptionOptions(skip_token_retrieval=True))
        assert isinstance(result, Destination)
        assert result.properties.get("clientId") == "my-client-id"
        _, kwargs = mock_http.request.call_args
        assert kwargs.get("params") == {"$skipTokenRetrieval": "true"}

    def test_get_destination_no_skip_token_retrieval_by_default(self, mock_http, destination_client):
        """Test that skip_token_retrieval=False (default) sends no $skipTokenRetrieval param."""
        _make_simple_resp(mock_http)
        destination_client.get_destination("my-api")
        _, kwargs = mock_http.request.call_args
        assert kwargs.get("params") is None


class TestDestinationClientWriteOperations:

    def test_create_destination_success(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(201)
        dest = Destination(name="new-dest", type="HTTP", url="https://api.example.com")
        result = destination_client.create_destination(dest, level=Level.SUB_ACCOUNT)
        assert result is None
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinations"
        assert kwargs["json"] == dest.to_dict()

    def test_create_destination_with_tenant(self, mock_http, destination_client):
        dest = Destination(name="new-dest", type="HTTP", url="https://api.example.com")
        destination_client.create_destination(dest, level=Level.SUB_ACCOUNT, tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_create_destination_without_tenant_uses_provider_context(self, mock_http, destination_client):
        destination_client.create_destination(Destination(name="new-dest", type="HTTP"))
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_create_destination_http_error_propagates(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(400)
        with pytest.raises(HttpError):
            destination_client.create_destination(Destination(name="d", type="HTTP"))

    def test_create_destination_unexpected_error_wrapped(self, mock_http, destination_client):
        mock_http.request.side_effect = Exception("boom")
        with pytest.raises(DestinationOperationError, match="failed to create destination 'x'"):
            destination_client.create_destination(Destination(name="x", type="HTTP"))

    def test_update_destination_success(self, mock_http, destination_client):
        dest = Destination(name="upd-dest", type="HTTP", description="updated")
        result = destination_client.update_destination(dest, level=Level.SUB_ACCOUNT)
        assert result is None
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinations"
        assert kwargs["json"] == dest.to_dict()

    def test_update_destination_with_tenant(self, mock_http, destination_client):
        destination_client.update_destination(Destination(name="upd-dest", type="HTTP"), level=Level.SUB_ACCOUNT, tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_update_destination_without_tenant_uses_provider_context(self, mock_http, destination_client):
        destination_client.update_destination(Destination(name="upd-dest", type="HTTP"))
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_update_destination_http_error_propagates(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(500)
        with pytest.raises(HttpError):
            destination_client.update_destination(Destination(name="d", type="HTTP"))

    def test_update_destination_unexpected_error_wrapped(self, mock_http, destination_client):
        mock_http.request.side_effect = Exception("boom")
        with pytest.raises(DestinationOperationError, match="failed to update destination 'd'"):
            destination_client.update_destination(Destination(name="d", type="HTTP"))

    def test_delete_destination_success(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(204)
        destination_client.delete_destination("to-del", level=Level.SUB_ACCOUNT)
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinations/to-del"
        assert kwargs["tenant_subdomain"] is None

    def test_delete_destination_with_tenant(self, mock_http, destination_client):
        destination_client.delete_destination("to-del", level=Level.SUB_ACCOUNT, tenant="test-tenant")
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinations/to-del"
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_delete_destination_without_tenant_uses_provider_context(self, mock_http, destination_client):
        destination_client.delete_destination("to-del")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_delete_destination_http_error_propagates(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(500)
        with pytest.raises(HttpError):
            destination_client.delete_destination("x")

    def test_delete_destination_unexpected_error_wrapped(self, mock_http, destination_client):
        mock_http.request.side_effect = Exception("boom")
        with pytest.raises(DestinationOperationError, match="failed to delete destination 'x'"):
            destination_client.delete_destination("x")


class TestDestinationClientInternalBehavior:

    def test_get_destination_invalid_json_wrapped(self, mock_http, destination_client):
        resp = _make_response(200)
        resp.json.side_effect = ValueError("bad json")
        mock_http.request.return_value = resp
        with pytest.raises(DestinationOperationError, match="invalid JSON in get destination response"):
            destination_client._get_destination(name="n", tenant_subdomain=None, level=Level.SUB_ACCOUNT)

    def test_sub_path_for_level(self):
        assert DestinationClient._sub_path_for_level(Level.SERVICE_INSTANCE) == "instanceDestinations"
        assert DestinationClient._sub_path_for_level(Level.SUB_ACCOUNT) == "subaccountDestinations"


class TestDestinationClientListOperations:
    """Test list_instance_destinations and list_subaccount_destinations methods."""

    def test_list_instance_destinations_success(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data=[
            {"name": "dest1", "type": "HTTP"},
            {"name": "dest2", "type": "HTTP"},
        ])
        result = destination_client.list_instance_destinations()
        assert isinstance(result, PagedResult)
        assert len(result.items) == 2
        assert all(isinstance(d, Destination) for d in result.items)
        assert result.items[0].name == "dest1"
        assert result.items[1].name == "dest2"
        assert result.pagination is None
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/instanceDestinations"
        assert kwargs.get("tenant_subdomain") is None
        assert kwargs.get("params") == {}

    def test_list_instance_destinations_empty_list(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data=[])
        result = destination_client.list_instance_destinations()
        assert isinstance(result, PagedResult)
        assert len(result.items) == 0
        assert result.pagination is None

    def test_list_instance_destinations_with_filter(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data=[{"name": "dest1", "type": "HTTP"}])
        filter_obj = ListOptions(filter_names=["dest1", "dest2"])
        result = destination_client.list_instance_destinations(filter=filter_obj)
        assert isinstance(result, PagedResult)
        assert len(result.items) == 1
        args, kwargs = mock_http.request.call_args
        assert "params" in kwargs
        assert "$filter" in kwargs["params"]
        assert "Name in" in kwargs["params"]["$filter"]

    def test_list_instance_destinations_http_error_wrapped(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(500, text="err")
        with pytest.raises(DestinationOperationError, match="failed to list instance destinations"):
            destination_client.list_instance_destinations()

    def test_list_instance_destinations_invalid_json_wrapped(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data={"not": "a list"})
        with pytest.raises(DestinationOperationError, match="expected list in response"):
            destination_client.list_instance_destinations()

    def test_list_instance_destinations_with_tenant(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data=[{"name": "dest1", "type": "HTTP"}])
        result = destination_client.list_instance_destinations(tenant="my-tenant")
        assert isinstance(result, PagedResult)
        assert len(result.items) == 1
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/instanceDestinations"
        assert kwargs.get("tenant_subdomain") == "my-tenant"

    def test_list_subaccount_destinations_requires_tenant_for_subscriber_access(self):
        client = DestinationClient(Mock())
        for strat in [AccessStrategy.SUBSCRIBER_ONLY, AccessStrategy.SUBSCRIBER_FIRST, AccessStrategy.PROVIDER_FIRST]:
            with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
                client.list_subaccount_destinations(access_strategy=strat, tenant=None)

    def test_list_subaccount_destinations_provider_only_no_tenant_required(self):
        client = DestinationClient(Mock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.PROVIDER_ONLY, tenant=None)
            assert result == paged_result
            mock_list.assert_called_once()
            called_kwargs = mock_list.call_args.kwargs
            assert called_kwargs.get("tenant_subdomain") is None
            assert called_kwargs.get("level") == Level.SUB_ACCOUNT

    def test_list_subaccount_destinations_subscriber_only_with_tenant(self):
        client = DestinationClient(Mock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.SUBSCRIBER_ONLY, tenant="tenant-1")
            assert result == paged_result
            mock_list.assert_called_once()
            called_kwargs = mock_list.call_args.kwargs
            assert called_kwargs.get("tenant_subdomain") == "tenant-1"

    def test_list_subaccount_destinations_subscriber_first_no_fallback(self):
        client = DestinationClient(Mock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-1")
            assert result == paged_result
            mock_list.assert_called_once()

    def test_list_subaccount_destinations_subscriber_first_fallback_to_provider(self):
        client = DestinationClient(Mock())
        empty_result = PagedResult(items=[])
        provider_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        with patch.object(client, "_list_destinations", side_effect=[empty_result, provider_result]) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-1")
            assert result == provider_result
            assert mock_list.call_count == 2
            assert mock_list.call_args_list[0].kwargs.get("tenant_subdomain") == "tenant-1"
            assert mock_list.call_args_list[1].kwargs.get("tenant_subdomain") is None

    def test_list_subaccount_destinations_provider_first_no_fallback(self):
        client = DestinationClient(Mock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="tenant-1")
            assert result == paged_result
            mock_list.assert_called_once()

    def test_list_subaccount_destinations_provider_first_fallback_to_subscriber(self):
        client = DestinationClient(Mock())
        empty_result = PagedResult(items=[])
        subscriber_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        with patch.object(client, "_list_destinations", side_effect=[empty_result, subscriber_result]) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="tenant-1")
            assert result == subscriber_result
            assert mock_list.call_count == 2
            assert mock_list.call_args_list[0].kwargs.get("tenant_subdomain") is None
            assert mock_list.call_args_list[1].kwargs.get("tenant_subdomain") == "tenant-1"

    def test_list_subaccount_destinations_with_filter(self):
        client = DestinationClient(Mock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        filter_obj = ListOptions(page=1, page_size=10)
        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.PROVIDER_ONLY, filter=filter_obj)
            assert result == paged_result
            called_kwargs = mock_list.call_args.kwargs
            assert called_kwargs.get("filter") == filter_obj

    def test_list_subaccount_destinations_http_error_wrapped(self):
        client = DestinationClient(Mock())
        with patch.object(client, "_list_destinations", side_effect=HttpError("bad", status_code=500)):
            with pytest.raises(DestinationOperationError, match="failed to list subaccount destinations"):
                client.list_subaccount_destinations(access_strategy=AccessStrategy.PROVIDER_ONLY)


class TestDestinationClientAccessStrategy:
    """Test the _apply_access_strategy helper method."""

    def test_apply_access_strategy_subscriber_only(self):
        client = DestinationClient(Mock())
        mock_fetch = Mock(return_value="result")
        result = client._apply_access_strategy(access_strategy=AccessStrategy.SUBSCRIBER_ONLY, tenant="tenant-1", fetch_func=mock_fetch)
        assert result == "result"
        mock_fetch.assert_called_once_with("tenant-1")

    def test_apply_access_strategy_provider_only(self):
        client = DestinationClient(Mock())
        mock_fetch = Mock(return_value="result")
        result = client._apply_access_strategy(access_strategy=AccessStrategy.PROVIDER_ONLY, tenant=None, fetch_func=mock_fetch)
        assert result == "result"
        mock_fetch.assert_called_once_with(None)

    def test_apply_access_strategy_subscriber_first_no_fallback(self):
        client = DestinationClient(Mock())
        mock_fetch = Mock(return_value="result")
        result = client._apply_access_strategy(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-1", fetch_func=mock_fetch)
        assert result == "result"
        mock_fetch.assert_called_once_with("tenant-1")

    def test_apply_access_strategy_subscriber_first_with_fallback(self):
        client = DestinationClient(Mock())
        mock_fetch = Mock(side_effect=[None, "provider-result"])
        result = client._apply_access_strategy(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-1", fetch_func=mock_fetch)
        assert result == "provider-result"
        assert mock_fetch.call_count == 2
        assert mock_fetch.call_args_list[0][0][0] == "tenant-1"
        assert mock_fetch.call_args_list[1][0][0] is None

    def test_apply_access_strategy_provider_first_no_fallback(self):
        client = DestinationClient(Mock())
        mock_fetch = Mock(return_value="result")
        result = client._apply_access_strategy(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="tenant-1", fetch_func=mock_fetch)
        assert result == "result"
        mock_fetch.assert_called_once_with(None)

    def test_apply_access_strategy_provider_first_with_fallback(self):
        client = DestinationClient(Mock())
        mock_fetch = Mock(side_effect=[None, "subscriber-result"])
        result = client._apply_access_strategy(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="tenant-1", fetch_func=mock_fetch)
        assert result == "subscriber-result"
        assert mock_fetch.call_count == 2
        assert mock_fetch.call_args_list[0][0][0] is None
        assert mock_fetch.call_args_list[1][0][0] == "tenant-1"

    def test_apply_access_strategy_requires_tenant_for_subscriber_strategies(self):
        client = DestinationClient(Mock())
        mock_fetch = Mock()
        for strat in [AccessStrategy.SUBSCRIBER_ONLY, AccessStrategy.SUBSCRIBER_FIRST, AccessStrategy.PROVIDER_FIRST]:
            with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
                client._apply_access_strategy(access_strategy=strat, tenant=None, fetch_func=mock_fetch)

    def test_apply_access_strategy_with_list_empty_value(self):
        """Test that empty PagedResult triggers fallback."""
        client = DestinationClient(Mock())
        empty_result = PagedResult(items=[])
        filled_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        mock_fetch = Mock(side_effect=[empty_result, filled_result])
        result = client._apply_access_strategy(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-1", fetch_func=mock_fetch)
        assert result == filled_result
        assert mock_fetch.call_count == 2


class TestDestinationClientEdgeCases:
    """Tests for edge cases and error handling in DestinationClient."""

    def test_get_subaccount_destination_unknown_access_strategy(self):
        """Test that unknown access strategy raises appropriate error."""
        client = DestinationClient(Mock())
        unknown_strategy = Mock()
        unknown_strategy.value = "UNKNOWN_STRATEGY"
        with pytest.raises(DestinationOperationError) as exc_info:
            client.get_subaccount_destination("test-dest", access_strategy=unknown_strategy, tenant="test-tenant")
        assert "unknown access strategy" in str(exc_info.value).lower()

    def test_list_destinations_non_list_response(self, mock_http, destination_client):
        """Test list destinations when response is not a list."""
        mock_http.request.return_value = _make_response(200, json_data={"error": "not a list"})
        with pytest.raises(DestinationOperationError) as exc_info:
            destination_client.list_instance_destinations()
        assert "expected list in response" in str(exc_info.value)

    def test_list_subaccount_destinations_both_empty_subscriber_first(self):
        """Test SUBSCRIBER_FIRST when both subscriber and provider return empty."""
        client = DestinationClient(Mock())
        empty_result = PagedResult(items=[])
        with patch.object(client, "_list_destinations", return_value=empty_result) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
            assert result == PagedResult(items=[])
            assert mock_list.call_count == 2

    def test_list_subaccount_destinations_both_empty_provider_first(self):
        """Test PROVIDER_FIRST when both provider and subscriber return empty."""
        client = DestinationClient(Mock())
        empty_result = PagedResult(items=[])
        with patch.object(client, "_list_destinations", return_value=empty_result) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="test-tenant")
            assert result == PagedResult(items=[])
            assert mock_list.call_count == 2

    def test_get_destination_malformed_destination_data(self, mock_http, destination_client):
        """Test get destination with malformed Destination data in response."""
        mock_http.request.return_value = _make_response(200, json_data={"name": "", "type": ""})
        with pytest.raises(DestinationOperationError) as exc_info:
            destination_client.get_instance_destination("test-dest")
        assert "invalid JSON in get destination response" in str(exc_info.value)

    def test_list_destinations_invalid_destination_in_array(self, mock_http, destination_client):
        """Test list destinations with invalid destination object in array - invalid destinations are skipped."""
        mock_http.request.return_value = _make_response(200, json_data=[
            {"name": "dest1", "type": "HTTP"},
            {"name": "", "type": ""},
        ])
        result = destination_client.list_instance_destinations()
        assert isinstance(result, PagedResult)
        assert len(result.items) == 1
        assert result.items[0].name == "dest1"

    def test_apply_access_strategy_unknown_strategy(self):
        """Test _apply_access_strategy with unknown strategy."""
        client = DestinationClient(Mock())
        unknown_strategy = Mock()
        unknown_strategy.value = "UNKNOWN"
        with pytest.raises(DestinationOperationError) as exc_info:
            client._apply_access_strategy(access_strategy=unknown_strategy, tenant="test-tenant", fetch_func=Mock(return_value="result"))
        assert "unknown access strategy" in str(exc_info.value).lower()

    def test_get_subaccount_destination_provider_first_both_none(self):
        """Test PROVIDER_FIRST when both provider and subscriber return None."""
        client = DestinationClient(Mock())
        with patch.object(client, "_get_destination", return_value=None) as mock_get:
            destination = client.get_subaccount_destination("test-dest", access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="test-tenant")
            assert destination is None
            assert mock_get.call_count == 2

    def test_get_subaccount_destination_subscriber_first_both_none(self):
        """Test SUBSCRIBER_FIRST when both subscriber and provider return None."""
        client = DestinationClient(Mock())
        with patch.object(client, "_get_destination", return_value=None) as mock_get:
            destination = client.get_subaccount_destination("test-dest", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant")
            assert destination is None
            assert mock_get.call_count == 2

    def test_list_destinations_with_http_403_error(self, mock_http, destination_client):
        """Test list destinations with 403 Forbidden error."""
        mock_http.request.return_value = _make_response(403, text="Forbidden")
        with pytest.raises(DestinationOperationError) as exc_info:
            destination_client.list_instance_destinations()
        assert "failed to list instance destinations" in str(exc_info.value)

    def test_get_destination_with_http_401_error(self, mock_http, destination_client):
        """Test get destination with 401 Unauthorized error."""
        mock_http.request.return_value = _make_response(401, text="Unauthorized")
        with pytest.raises(DestinationOperationError) as exc_info:
            destination_client.get_instance_destination("test-dest")
        assert "failed to get destination 'test-dest'" in str(exc_info.value)

    def test_list_destinations_json_parsing_error(self, mock_http, destination_client):
        """Test list destinations with JSON parsing error."""
        resp = _make_response(200)
        resp.headers = {}
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_http.request.return_value = resp
        with pytest.raises(DestinationOperationError) as exc_info:
            destination_client.list_instance_destinations()
        assert "invalid JSON in list destinations response" in str(exc_info.value)

    def test_apply_access_strategy_with_paged_result_empty_value(self):
        """Test _apply_access_strategy properly handles empty PagedResult objects."""
        client = DestinationClient(Mock())
        empty_paged = PagedResult(items=[])
        filled_paged = PagedResult(items=[Destination(name="d1", type="HTTP")])
        mock_fetch = Mock(side_effect=[empty_paged, filled_paged])
        result = client._apply_access_strategy(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant", fetch_func=mock_fetch)
        assert result is not None
        assert result == filled_paged
        assert len(result.items) == 1
        assert mock_fetch.call_count == 2

    def test_create_destination_with_connection_error(self, mock_http, destination_client):
        """Test create destination with connection error."""
        mock_http.request.side_effect = ConnectionError("Network unreachable")
        with pytest.raises(DestinationOperationError) as exc_info:
            destination_client.create_destination(Destination(name="test-dest", type="HTTP"))
        assert "failed to create destination 'test-dest'" in str(exc_info.value)
        assert "Network unreachable" in str(exc_info.value)

    def test_update_destination_with_timeout_error(self, mock_http, destination_client):
        """Test update destination with timeout error."""
        mock_http.request.side_effect = TimeoutError("Request timeout")
        with pytest.raises(DestinationOperationError) as exc_info:
            destination_client.update_destination(Destination(name="test-dest", type="HTTP"))
        assert "failed to update destination 'test-dest'" in str(exc_info.value)

    def test_delete_destination_with_runtime_error(self, mock_http, destination_client):
        """Test delete destination with runtime error."""
        mock_http.request.side_effect = RuntimeError("Unexpected runtime error")
        with pytest.raises(DestinationOperationError) as exc_info:
            destination_client.delete_destination("test-dest")
        assert "failed to delete destination 'test-dest'" in str(exc_info.value)

    def test_get_destination_with_non_404_http_error_propagates(self, mock_http, destination_client):
        """Test that non-404 HTTP errors are propagated correctly (not wrapped by _get_destination)."""
        mock_http.request.return_value = _make_response(502, text="Bad Gateway")
        with pytest.raises(HttpError) as exc_info:
            destination_client._get_destination(name="test-dest", tenant_subdomain=None, level=Level.SUB_ACCOUNT)
        assert exc_info.value.status_code == 502
        assert exc_info.value.response_text == "Bad Gateway"

    def test_list_destinations_with_malformed_json_items(self, mock_http, destination_client):
        """Test list destinations when JSON contains items that can't be parsed into Destination objects - malformed items are skipped."""
        mock_http.request.return_value = _make_response(200, json_data=[
            {"name": "dest1", "type": "HTTP"},
            {"invalid": "structure"},
        ])
        result = destination_client.list_instance_destinations()
        assert isinstance(result, PagedResult)
        assert len(result.items) == 1
        assert result.items[0].name == "dest1"

    def test_list_subaccount_destinations_with_filter_and_fallback(self):
        """Test that filter is correctly passed through fallback scenarios."""
        client = DestinationClient(Mock())
        empty_result = PagedResult(items=[])
        filled_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        filter_obj = ListOptions(filter_names=["d1"])
        with patch.object(client, "_list_destinations", side_effect=[empty_result, filled_result]) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="test-tenant", filter=filter_obj)
            assert result == filled_result
            assert mock_list.call_count == 2
            for call in mock_list.call_args_list:
                assert call.kwargs.get("filter") == filter_obj

    def test_apply_access_strategy_with_exception_in_fetch_func(self):
        """Test _apply_access_strategy when fetch_func raises an exception."""
        client = DestinationClient(Mock())
        mock_fetch = Mock(side_effect=ValueError("Fetch failed"))
        with pytest.raises(ValueError) as exc_info:
            client._apply_access_strategy(access_strategy=AccessStrategy.SUBSCRIBER_ONLY, tenant="test-tenant", fetch_func=mock_fetch)
        assert "Fetch failed" in str(exc_info.value)


class TestDestinationClientLabels:
    """Tests for DestinationClient label operations."""

    def test_get_destination_labels_instance(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data=[{"key": "env", "values": ["prod"]}])
        labels = destination_client.get_destination_labels("destA", Level.SERVICE_INSTANCE)
        assert len(labels) == 1
        assert labels[0].key == "env"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/instanceDestinations/destA/labels"
        assert kwargs["tenant_subdomain"] is None

    def test_get_destination_labels_subaccount(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data=[{"key": "team", "values": ["platform"]}])
        labels = destination_client.get_destination_labels("destA", Level.SUB_ACCOUNT)
        assert labels[0].key == "team"
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinations/destA/labels"
        assert kwargs["tenant_subdomain"] is None

    def test_get_destination_labels_default_level_is_subaccount(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data=[])
        destination_client.get_destination_labels("destA")
        args, kwargs = mock_http.request.call_args
        assert args[1] == "/v1/subaccountDestinations/destA/labels"
        assert kwargs["tenant_subdomain"] is None

    def test_get_destination_labels_non_list_response_raises(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data={"key": "env"})
        with pytest.raises(DestinationOperationError):
            destination_client.get_destination_labels("destA")

    def test_get_destination_labels_http_error_raises_operation_error(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(DestinationOperationError, match="failed to get labels for destination"):
            destination_client.get_destination_labels("destA")

    def test_update_destination_labels_instance(self, mock_http, destination_client):
        labels = [Label(key="env", values=["prod"])]
        destination_client.update_destination_labels("destA", labels, Level.SERVICE_INSTANCE)
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.PUT
        assert args[1] == "/v1/instanceDestinations/destA/labels"
        assert kwargs["json"] == [{"key": "env", "values": ["prod"]}]
        assert kwargs["tenant_subdomain"] is None

    def test_update_destination_labels_subaccount(self, mock_http, destination_client):
        labels = [Label(key="env", values=["staging"])]
        destination_client.update_destination_labels("destA", labels, Level.SUB_ACCOUNT)
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.PUT
        assert args[1] == "/v1/subaccountDestinations/destA/labels"
        assert kwargs["json"] == [{"key": "env", "values": ["staging"]}]
        assert kwargs["tenant_subdomain"] is None

    def test_update_destination_labels_http_error_propagates(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(HttpError):
            destination_client.update_destination_labels("destA", [], Level.SUB_ACCOUNT)

    def test_patch_destination_labels_instance(self, mock_http, destination_client):
        patch_obj = PatchLabels(action="ADD", labels=[Label(key="env", values=["prod"])])
        destination_client.patch_destination_labels("destA", patch_obj, Level.SERVICE_INSTANCE)
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.PATCH
        assert args[1] == "/v1/instanceDestinations/destA/labels"
        assert kwargs["json"] == {"action": "ADD", "labels": [{"key": "env", "values": ["prod"]}]}
        assert kwargs["tenant_subdomain"] is None

    def test_patch_destination_labels_subaccount(self, mock_http, destination_client):
        patch_obj = PatchLabels(action="DELETE", labels=[Label(key="env", values=[])])
        destination_client.patch_destination_labels("destA", patch_obj, Level.SUB_ACCOUNT)
        args, kwargs = mock_http.request.call_args
        assert args[0] == HttpMethod.PATCH
        assert args[1] == "/v1/subaccountDestinations/destA/labels"
        assert kwargs["json"] == {"action": "DELETE", "labels": [{"key": "env", "values": []}]}
        assert kwargs["tenant_subdomain"] is None

    def test_patch_destination_labels_http_error_propagates(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(404, text="Not Found")
        with pytest.raises(HttpError):
            destination_client.patch_destination_labels("destA", PatchLabels(action="ADD", labels=[]), Level.SUB_ACCOUNT)

    def test_get_destination_labels_with_tenant(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data=[])
        destination_client.get_destination_labels("destA", tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_get_destination_labels_without_tenant_uses_provider_context(self, mock_http, destination_client):
        mock_http.request.return_value = _make_response(200, json_data=[])
        destination_client.get_destination_labels("destA")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_update_destination_labels_with_tenant(self, mock_http, destination_client):
        destination_client.update_destination_labels("destA", [], tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_update_destination_labels_without_tenant_uses_provider_context(self, mock_http, destination_client):
        destination_client.update_destination_labels("destA", [])
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None

    def test_patch_destination_labels_with_tenant(self, mock_http, destination_client):
        destination_client.patch_destination_labels("destA", PatchLabels(action="ADD", labels=[]), tenant="test-tenant")
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] == "test-tenant"

    def test_patch_destination_labels_without_tenant_uses_provider_context(self, mock_http, destination_client):
        destination_client.patch_destination_labels("destA", PatchLabels(action="ADD", labels=[]))
        _, kwargs = mock_http.request.call_args
        assert kwargs["tenant_subdomain"] is None


_RESOLVER_PATCH = "sap_cloud_sdk.destination.client.read_from_mount_and_fallback_to_env_var"


class TestGetServiceInstanceId:
    """Tests for DestinationClient.get_service_instance_id()."""

    @patch(_RESOLVER_PATCH)
    def test_returns_instanceid_on_success(self, mock_read):
        def fill_instanceid(*args, **kwargs):
            kwargs["target"].instanceid = "my-instance-id"

        mock_read.side_effect = fill_instanceid
        client = DestinationClient(Mock())

        result = client.get_service_instance_id()

        assert result == "my-instance-id"
        mock_read.assert_called_once_with(
            base_volume_mount="/etc/secrets/appfnd",
            base_var_name="CLOUD_SDK_CFG",
            module="destination",
            instance="default",
            target=mock_read.call_args[1]["target"],
        )

    @patch(_RESOLVER_PATCH, side_effect=RuntimeError("mount failed"))
    def test_raises_on_exception(self, _mock_read):
        client = DestinationClient(Mock())
        with pytest.raises(DestinationOperationError, match="Could not resolve destination instance ID from secrets"):
            client.get_service_instance_id()
