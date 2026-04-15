"""Unit tests for DestinationClient operations and behaviors."""

import pytest
from unittest.mock import MagicMock, patch
from requests import Response

from sap_cloud_sdk.destination.client import DestinationClient
from sap_cloud_sdk.destination._models import (
    Destination,
    Label,
    Level,
    AccessStrategy,
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


class TestDestinationClientReadOperations:

    def test_get_instance_destination_success(self):
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {"name": "my-dest", "type": "HTTP"}
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        dest = client.get_instance_destination("my-dest")
        assert isinstance(dest, Destination)
        assert dest.name == "my-dest"
        assert dest.type == DestinationType.HTTP

        # Verify HTTP was called with instance path and no tenant
        args, kwargs = mock_http.get.call_args
        assert "instanceDestinations/my-dest" in args[0]
        assert kwargs.get("tenant_subdomain") is None

    def test_get_instance_destination_not_found_returns_none(self):
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpError("not found", status_code=404, response_text="Not Found")

        client = DestinationClient(mock_http)
        result = client.get_instance_destination("unknown")
        assert result is None

    def test_get_instance_destination_http_error_wrapped(self):
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpError("boom", status_code=500, response_text="err")

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError, match="failed to get destination 'my-dest'"):
            client.get_instance_destination("my-dest")

    def test_get_subaccount_destination_requires_tenant_for_subscriber_access(self):
        client = DestinationClient(MagicMock())

        for strat in [AccessStrategy.SUBSCRIBER_ONLY, AccessStrategy.SUBSCRIBER_FIRST, AccessStrategy.PROVIDER_FIRST]:
            with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
                client.get_subaccount_destination("my-dest", access_strategy=strat, tenant=None)

    def test_get_subaccount_destination_provider_only_no_tenant_required(self):
        client = DestinationClient(MagicMock())
        dest = Destination(name="prov-dest", type="HTTP")

        with patch.object(client, "_get_destination", return_value=dest) as mock_get:
            result = client.get_subaccount_destination("prov-dest", access_strategy=AccessStrategy.PROVIDER_ONLY, tenant=None)
            assert result is dest
            # Called once with provider context (no tenant)
            mock_get.assert_called_once()
            called_kwargs = mock_get.call_args.kwargs
            assert called_kwargs.get("tenant_subdomain") is None

    def test_get_subaccount_destination_subscriber_first_fallback_to_provider(self):
        client = DestinationClient(MagicMock())
        dest = Destination(name="my-dest", type="HTTP")

        with patch.object(client, "_get_destination", side_effect=[None, dest]) as mock_get:
            result = client.get_subaccount_destination("my-dest", access_strategy=AccessStrategy.SUBSCRIBER_FIRST, tenant="tenant-1")
            assert result is dest
            # First subscriber, then provider fallback
            assert mock_get.call_count == 2

    def test_get_subaccount_destination_provider_first_fallback_to_subscriber(self):
        client = DestinationClient(MagicMock())
        dest = Destination(name="my-dest", type="HTTP")

        with patch.object(client, "_get_destination", side_effect=[None, dest]) as mock_get:
            result = client.get_subaccount_destination("my-dest", access_strategy=AccessStrategy.PROVIDER_FIRST, tenant="tenant-1")
            assert result is dest
            # First provider, then subscriber fallback
            assert mock_get.call_count == 2

    def test_get_subaccount_destination_http_error_wrapped(self):
        client = DestinationClient(MagicMock())
        with patch.object(client, "_get_destination", side_effect=HttpError("bad", status_code=500)):
            with pytest.raises(DestinationOperationError, match="failed to get destination 'name'"):
                client.get_subaccount_destination("name", access_strategy=AccessStrategy.PROVIDER_ONLY)

    def test_get_destination_success(self):
        """Test successful destination consumption."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [
                {
                    "type": "Bearer",
                    "value": "dG9rZW4xMjM=",
                    "http_header": {
                        "key": "Authorization",
                        "value": "Bearer token123"
                    }
                }
            ],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.get_destination("my-api")

        assert isinstance(result, Destination)
        assert result.name == "my-api"
        assert result.url == "https://api.example.com"
        assert len(result.auth_tokens) == 1
        assert result.auth_tokens[0].type == "Bearer"
        assert result.auth_tokens[0].http_header["key"] == "Authorization"

        # Verify HTTP was called with v2 path
        args, kwargs = mock_http.get.call_args
        assert args[0] == "v2/destinations/my-api"
        assert kwargs.get("tenant_subdomain") is None
        assert kwargs.get("headers") == {}

    def test_get_destination_with_fragment_name(self):
        """Test consumption with fragment merging."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        options = ConsumptionOptions(fragment_name="production")
        result = client.get_destination("my-api", options=options)

        assert result is not None
        # Verify X-fragment-name header was sent
        args, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-fragment-name"] == "production"

    def test_get_destination_with_tenant_context(self):
        """Test consumption with tenant context for user token exchange."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [
                {
                    "type": "Bearer",
                    "value": "dXNlcnRva2Vu",
                    "http_header": {
                        "key": "Authorization",
                        "value": "Bearer usertoken"
                    },
                    "scope": "read write"
                }
            ],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        options = ConsumptionOptions(tenant="tenant-1")
        result = client.get_destination("my-api", options=options)

        assert isinstance(result, Destination)
        assert len(result.auth_tokens) == 1
        assert result.auth_tokens[0].scope == "read write"

        # Verify X-tenant header was passed
        args, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-tenant"] == "tenant-1"

    def test_get_destination_with_fragment_and_tenant(self):
        """Test consumption with both fragment and tenant."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        options = ConsumptionOptions(fragment_name="prod", tenant="tenant-1")
        result = client.get_destination("my-api", options=options)

        assert result is not None

        # Verify both fragment and tenant headers were passed
        args, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-fragment-name"] == "prod"
        assert kwargs["headers"]["X-tenant"] == "tenant-1"

    def test_get_destination_not_found_returns_none(self):
        """Test consumption returns None when destination not found."""
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpError("not found", status_code=404, response_text="Not Found")

        client = DestinationClient(mock_http)
        result = client.get_destination("unknown")

        assert result is None

    def test_get_destination_http_error_wrapped(self):
        """Test non-404 HTTP errors are wrapped."""
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpError("boom", status_code=500, response_text="Internal Error")

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError, match="failed to consume destination 'my-api'"):
            client.get_destination("my-api")

    def test_get_destination_invalid_json_wrapped(self):
        """Test invalid JSON response is wrapped."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError, match="failed to parse consume destination response"):
            client.get_destination("my-api")

    def test_get_destination_missing_destination_configuration(self):
        """Test response missing destinationConfiguration field."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "authTokens": [],
            "certificates": []
            # Missing destinationConfiguration
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError, match="failed to parse consume destination response"):
            client.get_destination("my-api")

    def test_get_destination_with_multiple_auth_tokens(self):
        """Test consumption with multiple auth tokens."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [
                {
                    "type": "Bearer",
                    "value": "dG9rZW4x",
                    "http_header": {"key": "Authorization", "value": "Bearer token1"}
                },
                {
                    "type": "ApiKey",
                    "value": "YXBpa2V5",
                    "http_header": {"key": "X-API-Key", "value": "apikey123"}
                }
            ],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.get_destination("my-api")

        assert isinstance(result, Destination)
        assert len(result.auth_tokens) == 2
        assert result.auth_tokens[0].type == "Bearer"
        assert result.auth_tokens[1].type == "ApiKey"

    def test_get_destination_with_certificates(self):
        """Test consumption returns certificates."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [],
            "certificates": [
                {
                    "Name": "client-cert",
                    "Content": "Y2VydGNvbnRlbnQ=",
                    "Type": "PEM"
                }
            ]
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.get_destination("my-api")

        assert isinstance(result, Destination)
        assert len(result.certificates) == 1
        assert result.certificates[0].name == "client-cert"
        assert result.certificates[0].type == "PEM"

    def test_get_destination_with_refresh_token(self):
        """Test auth token includes refresh token."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [
                {
                    "type": "Bearer",
                    "value": "dG9rZW4=",
                    "http_header": {"key": "Authorization", "value": "Bearer token"},
                    "refresh_token": "cmVmcmVzaA==",
                    "scope": "openid profile"
                }
            ],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.get_destination("my-api")

        assert isinstance(result, Destination)
        assert result.auth_tokens[0].refresh_token == "cmVmcmVzaA=="
        assert result.auth_tokens[0].scope == "openid profile"

    def test_get_destination_with_level_instance(self):
        """Test get_destination with level=SERVICE_INSTANCE uses @instance in path."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.get_destination("my-api", level=Level.SERVICE_INSTANCE)

        assert result is not None
        assert result.name == "my-api"

        # Verify path includes @instance
        args, kwargs = mock_http.get.call_args
        assert args[0] == "v2/destinations/my-api@instance"

    def test_get_destination_with_level_subaccount(self):
        """Test get_destination with level=SUB_ACCOUNT uses @subaccount in path."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.get_destination("my-api", level=Level.SUB_ACCOUNT)

        assert result is not None
        assert result.name == "my-api"

        # Verify path includes @subaccount
        args, kwargs = mock_http.get.call_args
        assert args[0] == "v2/destinations/my-api@subaccount"

    def test_get_destination_with_level_and_options(self):
        """Test get_destination combining level parameter with ConsumptionOptions."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        options = ConsumptionOptions(fragment_name="production", tenant="tenant-1")
        result = client.get_destination("my-api", level=Level.SUB_ACCOUNT, options=options)

        assert result is not None

        # Verify both level in path and options in headers
        args, kwargs = mock_http.get.call_args
        assert args[0] == "v2/destinations/my-api@subaccount"
        assert kwargs["headers"]["X-fragment-name"] == "production"
        assert kwargs["headers"]["X-tenant"] == "tenant-1"

    def test_get_destination_empty_auth_tokens_and_certificates(self):
        """Test consumption with no auth tokens or certificates."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com",
                "authentication": "NoAuthentication"
            },
            "authTokens": [],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.get_destination("my-api")

        assert isinstance(result, Destination)
        assert len(result.auth_tokens) == 0
        assert len(result.certificates) == 0

    def _make_simple_resp(self, mock_http):
        """Helper: configure mock_http to return a minimal valid v2 response."""
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {"name": "my-api", "type": "HTTP", "url": "https://api.example.com"},
            "authTokens": [],
            "certificates": [],
        }
        mock_http.get.return_value = resp

    def test_get_destination_with_fragment_optional_true(self):
        """X-fragment-optional: true is sent when fragment_optional=True."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination("my-api", options=ConsumptionOptions(fragment_name="prod", fragment_optional=True))

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-fragment-optional"] == "true"

    def test_get_destination_with_fragment_optional_false(self):
        """X-fragment-optional: false is sent when fragment_optional=False."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination("my-api", options=ConsumptionOptions(fragment_name="prod", fragment_optional=False))

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-fragment-optional"] == "false"

    def test_get_destination_fragment_optional_not_sent_when_none(self):
        """X-fragment-optional header is omitted when fragment_optional is not set."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination("my-api", options=ConsumptionOptions(fragment_name="prod"))

        _, kwargs = mock_http.get.call_args
        assert "X-fragment-optional" not in kwargs["headers"]

    def test_get_destination_with_user_token(self):
        """X-user-token header is sent for OAuth2UserTokenExchange flows."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination("my-api", options=ConsumptionOptions(user_token="my.jwt.token"))

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-user-token"] == "my.jwt.token"

    def test_get_destination_with_subject_token_and_type(self):
        """X-subject-token and X-subject-token-type are sent for OAuth2TokenExchange."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination(
            "my-api",
            options=ConsumptionOptions(
                subject_token="subj-token",
                subject_token_type="urn:ietf:params:oauth:token-type:access_token",
            ),
        )

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-subject-token"] == "subj-token"
        assert kwargs["headers"]["X-subject-token-type"] == "urn:ietf:params:oauth:token-type:access_token"

    def test_get_destination_with_actor_token_and_type(self):
        """X-actor-token and X-actor-token-type are sent for OAuth2TokenExchange."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination(
            "my-api",
            options=ConsumptionOptions(
                actor_token="actor-token",
                actor_token_type="urn:ietf:params:oauth:token-type:access_token",
            ),
        )

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-actor-token"] == "actor-token"
        assert kwargs["headers"]["X-actor-token-type"] == "urn:ietf:params:oauth:token-type:access_token"

    def test_get_destination_with_saml_assertion(self):
        """X-samlAssertion is sent for OAuth2SAMLBearerAssertion with ClientProvided."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination("my-api", options=ConsumptionOptions(saml_assertion="base64saml=="))

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-samlAssertion"] == "base64saml=="

    def test_get_destination_with_refresh_token(self):
        """X-refresh-token is sent for OAuth2RefreshToken destinations."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination("my-api", options=ConsumptionOptions(refresh_token="my-refresh-token"))

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-refresh-token"] == "my-refresh-token"

    def test_get_destination_with_code(self):
        """X-code is sent for OAuth2AuthorizationCode destinations."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination("my-api", options=ConsumptionOptions(code="auth-code-123"))

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-code"] == "auth-code-123"

    def test_get_destination_with_redirect_uri(self):
        """X-redirect-uri is sent for OAuth2AuthorizationCode destinations."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination(
            "my-api",
            options=ConsumptionOptions(code="auth-code-123", redirect_uri="https://app/callback"),
        )

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-redirect-uri"] == "https://app/callback"

    def test_get_destination_with_code_verifier(self):
        """X-code-verifier is sent for PKCE-enabled OAuth2AuthorizationCode destinations."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination(
            "my-api",
            options=ConsumptionOptions(code="auth-code-123", code_verifier="pkce-verifier-abc"),
        )

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-code-verifier"] == "pkce-verifier-abc"

    def test_get_destination_with_chain_name(self):
        """X-chain-name is sent when chain_name is provided."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination("my-api", options=ConsumptionOptions(chain_name="my-chain"))

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-chain-name"] == "my-chain"

    def test_get_destination_with_chain_vars(self):
        """X-chain-var-<name> headers are sent for each chain variable."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination(
            "my-api",
            options=ConsumptionOptions(
                chain_name="my-chain",
                chain_vars={"subject_token": "tok123", "subject_token_type": "access_token"},
            ),
        )

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-chain-name"] == "my-chain"
        assert kwargs["headers"]["X-chain-var-subject_token"] == "tok123"
        assert kwargs["headers"]["X-chain-var-subject_token_type"] == "access_token"

    def test_get_destination_chain_vars_without_chain_name(self):
        """chain_vars without chain_name: headers are still forwarded (API enforces pairing)."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination(
            "my-api",
            options=ConsumptionOptions(chain_vars={"subject_token": "tok"}),
        )

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-chain-var-subject_token"] == "tok"
        assert "X-chain-name" not in kwargs["headers"]

    def test_get_destination_all_headers_combined(self):
        """Multiple unrelated headers can be sent simultaneously."""
        mock_http = MagicMock()
        self._make_simple_resp(mock_http)

        client = DestinationClient(mock_http)
        client.get_destination(
            "my-api",
            options=ConsumptionOptions(
                fragment_name="prod",
                fragment_optional=True,
                tenant="tenant-1",
                user_token="user.jwt",
            ),
        )

        _, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-fragment-name"] == "prod"
        assert kwargs["headers"]["X-fragment-optional"] == "true"
        assert kwargs["headers"]["X-tenant"] == "tenant-1"
        assert kwargs["headers"]["X-user-token"] == "user.jwt"



    """Test suite for DestinationClient operations with transparent proxy enabled."""

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_instance_destination_with_proxy_enabled(self, mock_load_proxy):
        """Test get_instance_destination with proxy_enabled=True returns TransparentProxyDestination."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=True)

        result = client.get_instance_destination("my-dest", proxy_enabled=True)

        assert isinstance(result, TransparentProxyDestination)
        assert result.name == "my-dest"
        assert result.url == "http://test-proxy.test-ns"
        assert result.headers == {"X-destination-name": "my-dest"}

        # Verify HTTP was NOT called (bypassed by proxy)
        mock_http.get.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_instance_destination_with_proxy_disabled(self, mock_load_proxy):
        """Test get_instance_destination with proxy_enabled=False uses normal HTTP flow."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {"name": "my-dest", "type": "HTTP"}
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_instance_destination("my-dest", proxy_enabled=False)

        assert isinstance(result, Destination)
        assert result.name == "my-dest"

        # Verify HTTP was called (normal flow)
        mock_http.get.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_subaccount_destination_with_proxy_enabled(self, mock_load_proxy):
        """Test get_subaccount_destination with proxy_enabled=True returns TransparentProxyDestination."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=True)

        result = client.get_subaccount_destination(
            "my-dest",
            access_strategy=AccessStrategy.PROVIDER_ONLY,
            proxy_enabled=True
        )

        assert isinstance(result, TransparentProxyDestination)
        assert result.name == "my-dest"
        assert result.url == "http://test-proxy.test-ns"
        assert result.headers == {"X-destination-name": "my-dest"}

        # Verify HTTP was NOT called (bypassed by proxy)
        mock_http.get.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_subaccount_destination_with_proxy_disabled(self, mock_load_proxy):
        """Test get_subaccount_destination with proxy_enabled=False uses normal HTTP flow."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=True)

        dest = Destination(name="my-dest", type="HTTP")
        with patch.object(client, "_get_destination", return_value=dest) as mock_get:
            result = client.get_subaccount_destination(
                "my-dest",
                access_strategy=AccessStrategy.PROVIDER_ONLY,
                proxy_enabled=False
            )

            assert isinstance(result, Destination)
            assert result.name == "my-dest"

            # Verify _get_destination was called (normal flow)
            mock_get.assert_called_once()

    def test_get_subaccount_destination_proxy_enabled_no_proxy_configured_uses_normal_flow(self):
        """Test get_subaccount_destination with proxy_enabled=True but no proxy uses normal flow."""
        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=False)

        dest = Destination(name="my-dest", type="HTTP")
        with patch.object(client, "_get_destination", return_value=dest) as mock_get:
            result = client.get_subaccount_destination(
                "my-dest",
                access_strategy=AccessStrategy.PROVIDER_ONLY,
                proxy_enabled=True
            )

            # Should fall back to normal flow when proxy is not configured
            assert isinstance(result, Destination)
            mock_get.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_subaccount_destination_proxy_with_subscriber_strategy(self, mock_load_proxy):
        """Test get_subaccount_destination with proxy_enabled and SUBSCRIBER_FIRST strategy."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=True)

        result = client.get_subaccount_destination(
            "my-dest",
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant",
            proxy_enabled=True
        )

        assert isinstance(result, TransparentProxyDestination)
        assert result.name == "my-dest"

        # Even with tenant specified, proxy bypasses HTTP call
        mock_http.get.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_client_initialization_loads_proxy(self, mock_load_proxy):
        """Test that DestinationClient initialization calls load_transparent_proxy."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=True)

        # Verify load_transparent_proxy was called during initialization
        mock_load_proxy.assert_called_once()
        assert client._transparent_proxy == proxy

    def test_client_initialization_no_proxy(self):
        """Test that DestinationClient initialization handles no proxy configuration."""
        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=False)

        assert client._transparent_proxy is None

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_transparent_proxy_destination_url_format(self, mock_load_proxy):
        """Test that TransparentProxyDestination generates correct URL format."""
        proxy = TransparentProxy(proxy_name="my-proxy", namespace="my-namespace")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=True)

        result = client.get_instance_destination("test-destination", proxy_enabled=True)

        assert isinstance(result, TransparentProxyDestination)
        assert result.url == "http://my-proxy.my-namespace"
        assert result.headers == {"X-destination-name": "test-destination"}

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_transparent_proxy_destination_headers_format(self, mock_load_proxy):
        """Test that TransparentProxyDestination generates correct headers."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=True)

        destination_name = "complex-destination-name-123"
        result = client.get_instance_destination(destination_name, proxy_enabled=True)

        assert isinstance(result, TransparentProxyDestination)
        assert result.headers["X-destination-name"] == destination_name

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_instance_destination_default_proxy_disabled(self, mock_load_proxy):
        """Test that proxy_enabled defaults to client's use_default_proxy for get_instance_destination."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {"name": "my-dest", "type": "HTTP"}
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http, use_default_proxy=False)

        # Call without proxy_enabled parameter (should use client's default: False)
        result = client.get_instance_destination("my-dest")

        assert isinstance(result, Destination)
        # HTTP should be called since proxy is disabled by default
        mock_http.get.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_subaccount_destination_default_proxy_disabled(self, mock_load_proxy):
        """Test that proxy_enabled defaults to client's use_default_proxy for get_subaccount_destination."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=False)

        dest = Destination(name="my-dest", type="HTTP")
        with patch.object(client, "_get_destination", return_value=dest) as mock_get:
            # Call without proxy_enabled parameter (should use client's default: False)
            result = client.get_subaccount_destination(
                "my-dest",
                access_strategy=AccessStrategy.PROVIDER_ONLY
            )

            assert isinstance(result, Destination)
            # _get_destination should be called since proxy is disabled by default
            mock_get.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_with_proxy_enabled(self, mock_load_proxy):
        """Test get_destination (v2 API) with proxy_enabled=True returns TransparentProxyDestination."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=True)

        result = client.get_destination("my-api", proxy_enabled=True)

        assert isinstance(result, TransparentProxyDestination)
        assert result.name == "my-api"
        assert result.url == "http://test-proxy.test-ns"
        assert result.headers == {"X-destination-name": "my-api"}

        # Verify HTTP was NOT called (bypassed by proxy)
        mock_http.get.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_with_proxy_disabled(self, mock_load_proxy):
        """Test get_destination (v2 API) with proxy_enabled=False uses normal HTTP flow."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http, use_default_proxy=True)
        result = client.get_destination("my-api", proxy_enabled=False)

        assert isinstance(result, Destination)
        assert result.name == "my-api"
        assert result.url == "https://api.example.com"

        # Verify HTTP was called (normal flow)
        mock_http.get.assert_called_once()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_with_options_and_proxy_disabled(self, mock_load_proxy):
        """Test get_destination with ConsumptionOptions and proxy disabled."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http, use_default_proxy=False)
        options = ConsumptionOptions(fragment_name="prod", tenant="tenant-1")
        result = client.get_destination("my-api", options=options, proxy_enabled=False)

        assert isinstance(result, Destination)

        # Verify options were passed correctly
        args, kwargs = mock_http.get.call_args
        assert kwargs["headers"]["X-fragment-name"] == "prod"
        assert kwargs["headers"]["X-tenant"] == "tenant-1"

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_default_proxy_enabled(self, mock_load_proxy):
        """Test that proxy_enabled defaults to client's use_default_proxy for get_destination."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        client = DestinationClient(mock_http, use_default_proxy=True)

        # Call without proxy_enabled parameter (should use client's default: True)
        result = client.get_destination("my-api")

        assert isinstance(result, TransparentProxyDestination)
        # HTTP should NOT be called since proxy is enabled by default
        mock_http.get.assert_not_called()

    @patch("sap_cloud_sdk.destination.client.load_transparent_proxy")
    def test_get_destination_default_proxy_disabled(self, mock_load_proxy):
        """Test that get_destination uses normal flow when proxy is disabled by default."""
        proxy = TransparentProxy(proxy_name="test-proxy", namespace="test-ns")
        mock_load_proxy.return_value = proxy

        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {
            "destinationConfiguration": {
                "name": "my-api",
                "type": "HTTP",
                "url": "https://api.example.com"
            },
            "authTokens": [],
            "certificates": []
        }
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http, use_default_proxy=False)

        # Call without proxy_enabled parameter (should use client's default: False)
        result = client.get_destination("my-api")

        assert isinstance(result, Destination)
        # HTTP should be called since proxy is disabled by default
        mock_http.get.assert_called_once()


class TestDestinationClientWriteOperations:

    def test_create_destination_success(self):
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 201
        mock_http.post.return_value = resp

        client = DestinationClient(mock_http)
        dest = Destination(name="new-dest", type="HTTP", url="https://api.example.com")
        result = client.create_destination(dest, level=Level.SUB_ACCOUNT)

        assert result is None

        args, kwargs = mock_http.post.call_args
        assert args[0] == "v1/subaccountDestinations"
        assert kwargs["body"] == dest.to_dict()

    def test_create_destination_http_error_propagates(self):
        mock_http = MagicMock()
        mock_http.post.side_effect = HttpError("http fail", status_code=400)
        client = DestinationClient(mock_http)

        with pytest.raises(HttpError):
            client.create_destination(Destination(name="d", type="HTTP"))

    def test_create_destination_unexpected_error_wrapped(self):
        mock_http = MagicMock()
        mock_http.post.side_effect = Exception("boom")
        client = DestinationClient(mock_http)

        with pytest.raises(DestinationOperationError, match="failed to create destination 'x'"):
            client.create_destination(Destination(name="x", type="HTTP"))


    def test_update_destination_success(self):
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        mock_http.put.return_value = resp

        client = DestinationClient(mock_http)
        dest = Destination(name="upd-dest", type="HTTP", description="updated")
        result = client.update_destination(dest, level=Level.SUB_ACCOUNT)

        assert result is None

        args, kwargs = mock_http.put.call_args
        assert args[0] == "v1/subaccountDestinations"
        assert kwargs["body"] == dest.to_dict()

    def test_update_destination_http_error_propagates(self):
        mock_http = MagicMock()
        mock_http.put.side_effect = HttpError("http fail", status_code=500)
        client = DestinationClient(mock_http)

        with pytest.raises(HttpError):
            client.update_destination(Destination(name="d", type="HTTP"))

    def test_update_destination_unexpected_error_wrapped(self):
        mock_http = MagicMock()
        mock_http.put.side_effect = Exception("boom")
        client = DestinationClient(mock_http)

        with pytest.raises(DestinationOperationError, match="failed to update destination 'd'"):
            client.update_destination(Destination(name="d", type="HTTP"))

    def test_delete_destination_success(self):
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 204
        mock_http.delete.return_value = resp

        client = DestinationClient(mock_http)
        client.delete_destination("to-del", level=Level.SUB_ACCOUNT)

        args, kwargs = mock_http.delete.call_args
        assert args[0] == "v1/subaccountDestinations/to-del"

    def test_delete_destination_http_error_propagates(self):
        mock_http = MagicMock()
        mock_http.delete.side_effect = HttpError("http fail", status_code=500)
        client = DestinationClient(mock_http)

        with pytest.raises(HttpError):
            client.delete_destination("x")

    def test_delete_destination_unexpected_error_wrapped(self):
        mock_http = MagicMock()
        mock_http.delete.side_effect = Exception("boom")
        client = DestinationClient(mock_http)

        with pytest.raises(DestinationOperationError, match="failed to delete destination 'x'"):
            client.delete_destination("x")


class TestDestinationClientInternalBehavior:

    def test_get_destination_invalid_json_wrapped(self):
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        # Simulate invalid JSON parsing
        resp.json.side_effect = ValueError("bad json")
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError, match="invalid JSON in get destination response"):
            client._get_destination(name="n", tenant_subdomain=None, level=Level.SUB_ACCOUNT)

    def test_sub_path_for_level(self):
        assert DestinationClient._sub_path_for_level(Level.SERVICE_INSTANCE) == "instanceDestinations"
        assert DestinationClient._sub_path_for_level(Level.SUB_ACCOUNT) == "subaccountDestinations"


class TestDestinationClientListOperations:
    """Test list_instance_destinations and list_subaccount_destinations methods."""

    def test_list_instance_destinations_success(self):
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.headers = {}
        resp.json.return_value = [
            {"name": "dest1", "type": "HTTP"},
            {"name": "dest2", "type": "HTTP"}
        ]
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.list_instance_destinations()

        assert isinstance(result, PagedResult)
        assert len(result.items) == 2
        assert all(isinstance(d, Destination) for d in result.items)
        assert result.items[0].name == "dest1"
        assert result.items[1].name == "dest2"
        assert result.pagination is None  # No pagination headers

        # Verify HTTP was called with instance path, no tenant, and no params
        args, kwargs = mock_http.get.call_args
        assert args[0] == "v1/instanceDestinations"
        assert kwargs.get("tenant_subdomain") is None
        assert kwargs.get("params") == {}

    def test_list_instance_destinations_empty_list(self):
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.headers = {}
        resp.json.return_value = []
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.list_instance_destinations()

        assert isinstance(result, PagedResult)
        assert len(result.items) == 0
        assert result.pagination is None

    def test_list_instance_destinations_with_filter(self):
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.headers = {}
        resp.json.return_value = [{"name": "dest1", "type": "HTTP"}]
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        filter_obj = ListOptions(filter_names=["dest1", "dest2"])
        result = client.list_instance_destinations(filter=filter_obj)

        assert isinstance(result, PagedResult)
        assert len(result.items) == 1

        # Verify params were passed
        args, kwargs = mock_http.get.call_args
        assert "params" in kwargs
        assert "$filter" in kwargs["params"]
        assert "Name in" in kwargs["params"]["$filter"]

    def test_list_instance_destinations_http_error_wrapped(self):
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpError("boom", status_code=500, response_text="err")

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError, match="failed to list instance destinations"):
            client.list_instance_destinations()

    def test_list_instance_destinations_invalid_json_wrapped(self):
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.json.return_value = {"not": "a list"}  # Should be a list
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError, match="expected list in response"):
            client.list_instance_destinations()

    def test_list_subaccount_destinations_requires_tenant_for_subscriber_access(self):
        client = DestinationClient(MagicMock())

        for strat in [AccessStrategy.SUBSCRIBER_ONLY, AccessStrategy.SUBSCRIBER_FIRST, AccessStrategy.PROVIDER_FIRST]:
            with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
                client.list_subaccount_destinations(access_strategy=strat, tenant=None)

    def test_list_subaccount_destinations_provider_only_no_tenant_required(self):
        client = DestinationClient(MagicMock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])

        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(access_strategy=AccessStrategy.PROVIDER_ONLY, tenant=None)
            assert result == paged_result
            # Called once with provider context (no tenant)
            mock_list.assert_called_once()
            called_kwargs = mock_list.call_args.kwargs
            assert called_kwargs.get("tenant_subdomain") is None
            assert called_kwargs.get("level") == Level.SUB_ACCOUNT

    def test_list_subaccount_destinations_subscriber_only_with_tenant(self):
        client = DestinationClient(MagicMock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])

        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(
                access_strategy=AccessStrategy.SUBSCRIBER_ONLY,
                tenant="tenant-1"
            )
            assert result == paged_result
            # Called once with subscriber context
            mock_list.assert_called_once()
            called_kwargs = mock_list.call_args.kwargs
            assert called_kwargs.get("tenant_subdomain") == "tenant-1"

    def test_list_subaccount_destinations_subscriber_first_no_fallback(self):
        client = DestinationClient(MagicMock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])

        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(
                access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
                tenant="tenant-1"
            )
            assert result == paged_result
            # Found in subscriber, no fallback needed
            mock_list.assert_called_once()

    def test_list_subaccount_destinations_subscriber_first_fallback_to_provider(self):
        client = DestinationClient(MagicMock())
        empty_result = PagedResult(items=[])
        provider_result = PagedResult(items=[Destination(name="d1", type="HTTP")])

        with patch.object(client, "_list_destinations", side_effect=[empty_result, provider_result]) as mock_list:
            result = client.list_subaccount_destinations(
                access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
                tenant="tenant-1"
            )
            assert result == provider_result
            # First subscriber (empty), then provider fallback
            assert mock_list.call_count == 2
            # First call with tenant
            assert mock_list.call_args_list[0].kwargs.get("tenant_subdomain") == "tenant-1"
            # Second call without tenant (provider)
            assert mock_list.call_args_list[1].kwargs.get("tenant_subdomain") is None

    def test_list_subaccount_destinations_provider_first_no_fallback(self):
        client = DestinationClient(MagicMock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])

        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(
                access_strategy=AccessStrategy.PROVIDER_FIRST,
                tenant="tenant-1"
            )
            assert result == paged_result
            # Found in provider, no fallback needed
            mock_list.assert_called_once()

    def test_list_subaccount_destinations_provider_first_fallback_to_subscriber(self):
        client = DestinationClient(MagicMock())
        empty_result = PagedResult(items=[])
        subscriber_result = PagedResult(items=[Destination(name="d1", type="HTTP")])

        with patch.object(client, "_list_destinations", side_effect=[empty_result, subscriber_result]) as mock_list:
            result = client.list_subaccount_destinations(
                access_strategy=AccessStrategy.PROVIDER_FIRST,
                tenant="tenant-1"
            )
            assert result == subscriber_result
            # First provider (empty), then subscriber fallback
            assert mock_list.call_count == 2
            # First call without tenant (provider)
            assert mock_list.call_args_list[0].kwargs.get("tenant_subdomain") is None
            # Second call with tenant
            assert mock_list.call_args_list[1].kwargs.get("tenant_subdomain") == "tenant-1"

    def test_list_subaccount_destinations_with_filter(self):
        client = DestinationClient(MagicMock())
        paged_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        filter_obj = ListOptions(page=1, page_size=10)

        with patch.object(client, "_list_destinations", return_value=paged_result) as mock_list:
            result = client.list_subaccount_destinations(
                access_strategy=AccessStrategy.PROVIDER_ONLY,
                filter=filter_obj
            )
            assert result == paged_result
            # Verify filter was passed
            called_kwargs = mock_list.call_args.kwargs
            assert called_kwargs.get("filter") == filter_obj

    def test_list_subaccount_destinations_http_error_wrapped(self):
        client = DestinationClient(MagicMock())
        with patch.object(client, "_list_destinations", side_effect=HttpError("bad", status_code=500)):
            with pytest.raises(DestinationOperationError, match="failed to list subaccount destinations"):
                client.list_subaccount_destinations(access_strategy=AccessStrategy.PROVIDER_ONLY)


class TestDestinationClientAccessStrategy:
    """Test the _apply_access_strategy helper method."""

    def test_apply_access_strategy_subscriber_only(self):
        client = DestinationClient(MagicMock())
        mock_fetch = MagicMock(return_value="result")

        result = client._apply_access_strategy(
            access_strategy=AccessStrategy.SUBSCRIBER_ONLY,
            tenant="tenant-1",
            fetch_func=mock_fetch
        )

        assert result == "result"
        mock_fetch.assert_called_once_with("tenant-1")

    def test_apply_access_strategy_provider_only(self):
        client = DestinationClient(MagicMock())
        mock_fetch = MagicMock(return_value="result")

        result = client._apply_access_strategy(
            access_strategy=AccessStrategy.PROVIDER_ONLY,
            tenant=None,
            fetch_func=mock_fetch
        )

        assert result == "result"
        mock_fetch.assert_called_once_with(None)

    def test_apply_access_strategy_subscriber_first_no_fallback(self):
        client = DestinationClient(MagicMock())
        mock_fetch = MagicMock(return_value="result")

        result = client._apply_access_strategy(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="tenant-1",
            fetch_func=mock_fetch
        )

        assert result == "result"
        # Called once, found result in subscriber
        mock_fetch.assert_called_once_with("tenant-1")

    def test_apply_access_strategy_subscriber_first_with_fallback(self):
        client = DestinationClient(MagicMock())
        mock_fetch = MagicMock(side_effect=[None, "provider-result"])

        result = client._apply_access_strategy(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="tenant-1",
            fetch_func=mock_fetch
        )

        assert result == "provider-result"
        # Called twice: subscriber returned None, then provider
        assert mock_fetch.call_count == 2
        assert mock_fetch.call_args_list[0][0][0] == "tenant-1"
        assert mock_fetch.call_args_list[1][0][0] is None

    def test_apply_access_strategy_provider_first_no_fallback(self):
        client = DestinationClient(MagicMock())
        mock_fetch = MagicMock(return_value="result")

        result = client._apply_access_strategy(
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="tenant-1",
            fetch_func=mock_fetch
        )

        assert result == "result"
        # Called once, found result in provider
        mock_fetch.assert_called_once_with(None)

    def test_apply_access_strategy_provider_first_with_fallback(self):
        client = DestinationClient(MagicMock())
        mock_fetch = MagicMock(side_effect=[None, "subscriber-result"])

        result = client._apply_access_strategy(
            access_strategy=AccessStrategy.PROVIDER_FIRST,
            tenant="tenant-1",
            fetch_func=mock_fetch
        )

        assert result == "subscriber-result"
        # Called twice: provider returned None, then subscriber
        assert mock_fetch.call_count == 2
        assert mock_fetch.call_args_list[0][0][0] is None
        assert mock_fetch.call_args_list[1][0][0] == "tenant-1"

    def test_apply_access_strategy_requires_tenant_for_subscriber_strategies(self):
        client = DestinationClient(MagicMock())
        mock_fetch = MagicMock()

        for strat in [AccessStrategy.SUBSCRIBER_ONLY, AccessStrategy.SUBSCRIBER_FIRST, AccessStrategy.PROVIDER_FIRST]:
            with pytest.raises(DestinationOperationError, match="tenant subdomain must be provided"):
                client._apply_access_strategy(
                    access_strategy=strat,
                    tenant=None,
                    fetch_func=mock_fetch
                )

    def test_apply_access_strategy_with_list_empty_value(self):
        """Test that empty PagedResult triggers fallback."""
        client = DestinationClient(MagicMock())
        empty_result = PagedResult(items=[])
        filled_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        mock_fetch = MagicMock(side_effect=[empty_result, filled_result])

        result = client._apply_access_strategy(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="tenant-1",
            fetch_func=mock_fetch
        )

        assert result == filled_result
        # Empty PagedResult triggered fallback
        assert mock_fetch.call_count == 2


class TestDestinationClientEdgeCases:
    """Tests for edge cases and error handling in DestinationClient."""

    def test_get_subaccount_destination_unknown_access_strategy(self):
        """Test that unknown access strategy raises appropriate error."""
        from unittest.mock import Mock as MockStrategy

        client = DestinationClient(MagicMock())
        unknown_strategy = MockStrategy()
        unknown_strategy.value = "UNKNOWN_STRATEGY"

        with pytest.raises(DestinationOperationError) as exc_info:
            client.get_subaccount_destination(
                "test-dest",
                access_strategy=unknown_strategy,  # ty: ignore[invalid-argument-type]
                tenant="test-tenant"
            )

        assert "unknown access strategy" in str(exc_info.value).lower()

    def test_list_destinations_non_list_response(self):
        """Test list destinations when response is not a list."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.headers = {}
        resp.json.return_value = {"error": "not a list"}
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError) as exc_info:
            client.list_instance_destinations()

        assert "expected list in response" in str(exc_info.value)

    def test_list_subaccount_destinations_both_empty_subscriber_first(self):
        """Test SUBSCRIBER_FIRST when both subscriber and provider return empty."""
        client = DestinationClient(MagicMock())
        empty_result = PagedResult(items=[])

        with patch.object(client, "_list_destinations", return_value=empty_result) as mock_list:
            result = client.list_subaccount_destinations(
                access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
                tenant="test-tenant"
            )

            assert result == PagedResult(items=[])
            assert mock_list.call_count == 2

    def test_list_subaccount_destinations_both_empty_provider_first(self):
        """Test PROVIDER_FIRST when both provider and subscriber return empty."""
        client = DestinationClient(MagicMock())
        empty_result = PagedResult(items=[])

        with patch.object(client, "_list_destinations", return_value=empty_result) as mock_list:
            result = client.list_subaccount_destinations(
                access_strategy=AccessStrategy.PROVIDER_FIRST,
                tenant="test-tenant"
            )

            assert result == PagedResult(items=[])
            assert mock_list.call_count == 2

    def test_get_destination_malformed_destination_data(self):
        """Test get destination with malformed Destination data in response."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.headers = {}
        # Missing required fields for Destination.from_dict
        resp.json.return_value = {"name": "", "type": ""}
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError) as exc_info:
            client.get_instance_destination("test-dest")

        assert "invalid JSON in get destination response" in str(exc_info.value)

    def test_list_destinations_invalid_destination_in_array(self):
        """Test list destinations with invalid destination object in array - invalid destinations are skipped."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.headers = {}
        # One valid, one invalid destination
        resp.json.return_value = [
            {"name": "dest1", "type": "HTTP"},
            {"name": "", "type": ""}  # Invalid - will be skipped
        ]
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.list_instance_destinations()

        # Should return only the valid destination, skipping the invalid one
        assert isinstance(result, PagedResult)
        assert len(result.items) == 1
        assert result.items[0].name == "dest1"

    def test_apply_access_strategy_unknown_strategy(self):
        """Test _apply_access_strategy with unknown strategy."""
        from unittest.mock import Mock as MockStrategy

        client = DestinationClient(MagicMock())
        unknown_strategy = MockStrategy()
        unknown_strategy.value = "UNKNOWN"

        mock_fetch = MagicMock(return_value="result")

        with pytest.raises(DestinationOperationError) as exc_info:
            client._apply_access_strategy(
                access_strategy=unknown_strategy,  # ty: ignore[invalid-argument-type]
                tenant="test-tenant",
                fetch_func=mock_fetch
            )

        assert "unknown access strategy" in str(exc_info.value).lower()

    def test_get_subaccount_destination_provider_first_both_none(self):
        """Test PROVIDER_FIRST when both provider and subscriber return None."""
        client = DestinationClient(MagicMock())

        with patch.object(client, "_get_destination", return_value=None) as mock_get:
            destination = client.get_subaccount_destination(
                "test-dest",
                access_strategy=AccessStrategy.PROVIDER_FIRST,
                tenant="test-tenant"
            )

            assert destination is None
            assert mock_get.call_count == 2

    def test_get_subaccount_destination_subscriber_first_both_none(self):
        """Test SUBSCRIBER_FIRST when both subscriber and provider return None."""
        client = DestinationClient(MagicMock())

        with patch.object(client, "_get_destination", return_value=None) as mock_get:
            destination = client.get_subaccount_destination(
                "test-dest",
                access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
                tenant="test-tenant"
            )

            assert destination is None
            assert mock_get.call_count == 2

    def test_list_destinations_with_http_403_error(self):
        """Test list destinations with 403 Forbidden error."""
        mock_http = MagicMock()
        http_error = HttpError("Forbidden", status_code=403, response_text="Forbidden")
        mock_http.get.side_effect = http_error

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError) as exc_info:
            client.list_instance_destinations()

        assert "failed to list instance destinations" in str(exc_info.value)

    def test_get_destination_with_http_401_error(self):
        """Test get destination with 401 Unauthorized error."""
        mock_http = MagicMock()
        http_error = HttpError("Unauthorized", status_code=401, response_text="Unauthorized")
        mock_http.get.side_effect = http_error

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError) as exc_info:
            client.get_instance_destination("test-dest")

        assert "failed to get destination 'test-dest'" in str(exc_info.value)

    def test_list_destinations_json_parsing_error(self):
        """Test list destinations with JSON parsing error."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.headers = {}
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError) as exc_info:
            client.list_instance_destinations()

        assert "invalid JSON in list destinations response" in str(exc_info.value)

    def test_apply_access_strategy_with_paged_result_empty_value(self):
        """Test _apply_access_strategy properly handles empty PagedResult objects."""
        client = DestinationClient(MagicMock())

        empty_paged = PagedResult(items=[])
        filled_paged = PagedResult(items=[Destination(name="d1", type="HTTP")])

        mock_fetch = MagicMock(side_effect=[empty_paged, filled_paged])

        result = client._apply_access_strategy(
            access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
            tenant="test-tenant",
            fetch_func=mock_fetch
        )

        assert result is not None
        assert result == filled_paged
        assert len(result.items) == 1
        assert mock_fetch.call_count == 2

    def test_create_destination_with_connection_error(self):
        """Test create destination with connection error."""
        mock_http = MagicMock()
        mock_http.post.side_effect = ConnectionError("Network unreachable")

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError) as exc_info:
            client.create_destination(Destination(name="test-dest", type="HTTP"))

        assert "failed to create destination 'test-dest'" in str(exc_info.value)
        assert "Network unreachable" in str(exc_info.value)

    def test_update_destination_with_timeout_error(self):
        """Test update destination with timeout error."""
        mock_http = MagicMock()
        mock_http.put.side_effect = TimeoutError("Request timeout")

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError) as exc_info:
            client.update_destination(Destination(name="test-dest", type="HTTP"))

        assert "failed to update destination 'test-dest'" in str(exc_info.value)

    def test_delete_destination_with_runtime_error(self):
        """Test delete destination with runtime error."""
        mock_http = MagicMock()
        mock_http.delete.side_effect = RuntimeError("Unexpected runtime error")

        client = DestinationClient(mock_http)
        with pytest.raises(DestinationOperationError) as exc_info:
            client.delete_destination("test-dest")

        assert "failed to delete destination 'test-dest'" in str(exc_info.value)

    def test_get_destination_with_non_404_http_error_propagates(self):
        """Test that non-404 HTTP errors are propagated correctly (not wrapped by _get_destination)."""
        mock_http = MagicMock()
        http_error = HttpError("Bad Gateway", status_code=502, response_text="Bad Gateway")
        mock_http.get.side_effect = http_error

        client = DestinationClient(mock_http)
        # _get_destination propagates non-404 HttpErrors directly
        with pytest.raises(HttpError) as exc_info:
            client._get_destination(name="test-dest", tenant_subdomain=None, level=Level.SUB_ACCOUNT)

        # The error should not return None (which is reserved for 404)
        # It should raise HttpError directly
        assert exc_info.value.status_code == 502
        assert "Bad Gateway" in str(exc_info.value)

    def test_list_destinations_with_malformed_json_items(self):
        """Test list destinations when JSON contains items that can't be parsed into Destination objects - malformed items are skipped."""
        mock_http = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        resp.headers = {}
        # Valid list structure but some items can't be converted to Destination
        resp.json.return_value = [
            {"name": "dest1", "type": "HTTP"},
            {"invalid": "structure"}  # Missing required 'name' and 'type' - will be skipped
        ]
        mock_http.get.return_value = resp

        client = DestinationClient(mock_http)
        result = client.list_instance_destinations()

        # Should return only the valid destination, skipping the malformed one
        assert isinstance(result, PagedResult)
        assert len(result.items) == 1
        assert result.items[0].name == "dest1"

    def test_list_subaccount_destinations_with_filter_and_fallback(self):
        """Test that filter is correctly passed through fallback scenarios."""
        client = DestinationClient(MagicMock())
        empty_result = PagedResult(items=[])
        filled_result = PagedResult(items=[Destination(name="d1", type="HTTP")])
        filter_obj = ListOptions(filter_names=["d1"])

        with patch.object(client, "_list_destinations", side_effect=[empty_result, filled_result]) as mock_list:
            result = client.list_subaccount_destinations(
                access_strategy=AccessStrategy.SUBSCRIBER_FIRST,
                tenant="test-tenant",
                filter=filter_obj
            )

            assert result == filled_result
            assert mock_list.call_count == 2
            # Verify filter was passed to both calls
            for call in mock_list.call_args_list:
                assert call.kwargs.get("filter") == filter_obj

    def test_apply_access_strategy_with_exception_in_fetch_func(self):
        """Test _apply_access_strategy when fetch_func raises an exception."""
        client = DestinationClient(MagicMock())
        mock_fetch = MagicMock(side_effect=ValueError("Fetch failed"))

        with pytest.raises(ValueError) as exc_info:
            client._apply_access_strategy(
                access_strategy=AccessStrategy.SUBSCRIBER_ONLY,
                tenant="test-tenant",
                fetch_func=mock_fetch
            )

        assert "Fetch failed" in str(exc_info.value)


class TestDestinationClientLabels:
    """Tests for DestinationClient label operations."""

    def test_get_destination_labels_instance(self):
        mock_http = MagicMock()
        mock_http.get.return_value.json.return_value = [{"key": "env", "values": ["prod"]}]
        client = DestinationClient(mock_http)

        labels = client.get_destination_labels("destA", Level.SERVICE_INSTANCE)

        assert len(labels) == 1
        assert labels[0].key == "env"
        mock_http.get.assert_called_once_with("v1/instanceDestinations/destA/labels")

    def test_get_destination_labels_subaccount(self):
        mock_http = MagicMock()
        mock_http.get.return_value.json.return_value = [{"key": "team", "values": ["platform"]}]
        client = DestinationClient(mock_http)

        labels = client.get_destination_labels("destA", Level.SUB_ACCOUNT)

        assert labels[0].key == "team"
        mock_http.get.assert_called_once_with("v1/subaccountDestinations/destA/labels")

    def test_get_destination_labels_default_level_is_subaccount(self):
        mock_http = MagicMock()
        mock_http.get.return_value.json.return_value = []
        client = DestinationClient(mock_http)

        client.get_destination_labels("destA")

        mock_http.get.assert_called_once_with("v1/subaccountDestinations/destA/labels")

    def test_get_destination_labels_non_list_response_raises(self):
        mock_http = MagicMock()
        mock_http.get.return_value.json.return_value = {"key": "env"}
        client = DestinationClient(mock_http)

        with pytest.raises(DestinationOperationError):
            client.get_destination_labels("destA")

    def test_get_destination_labels_http_error_raises_operation_error(self):
        mock_http = MagicMock()
        mock_http.get.side_effect = HttpError("Not Found", status_code=404, response_text="Not Found")
        client = DestinationClient(mock_http)

        with pytest.raises(DestinationOperationError, match="failed to get labels for destination"):
            client.get_destination_labels("destA")

    def test_update_destination_labels_instance(self):
        mock_http = MagicMock()
        client = DestinationClient(mock_http)
        labels = [Label(key="env", values=["prod"])]

        client.update_destination_labels("destA", labels, Level.SERVICE_INSTANCE)

        mock_http.put.assert_called_once_with(
            "v1/instanceDestinations/destA/labels",
            body=[{"key": "env", "values": ["prod"]}],
        )

    def test_update_destination_labels_subaccount(self):
        mock_http = MagicMock()
        client = DestinationClient(mock_http)
        labels = [Label(key="env", values=["staging"])]

        client.update_destination_labels("destA", labels, Level.SUB_ACCOUNT)

        mock_http.put.assert_called_once_with(
            "v1/subaccountDestinations/destA/labels",
            body=[{"key": "env", "values": ["staging"]}],
        )

    def test_update_destination_labels_http_error_propagates(self):
        mock_http = MagicMock()
        mock_http.put.side_effect = HttpError("Not Found", status_code=404, response_text="Not Found")
        client = DestinationClient(mock_http)

        with pytest.raises(HttpError):
            client.update_destination_labels("destA", [], Level.SUB_ACCOUNT)

    def test_patch_destination_labels_instance(self):
        mock_http = MagicMock()
        client = DestinationClient(mock_http)
        patch = PatchLabels(action="ADD", labels=[Label(key="env", values=["prod"])])

        client.patch_destination_labels("destA", patch, Level.SERVICE_INSTANCE)

        mock_http.patch.assert_called_once_with(
            "v1/instanceDestinations/destA/labels",
            body={"action": "ADD", "labels": [{"key": "env", "values": ["prod"]}]},
        )

    def test_patch_destination_labels_subaccount(self):
        mock_http = MagicMock()
        client = DestinationClient(mock_http)
        patch = PatchLabels(action="DELETE", labels=[Label(key="env", values=[])])

        client.patch_destination_labels("destA", patch, Level.SUB_ACCOUNT)

        mock_http.patch.assert_called_once_with(
            "v1/subaccountDestinations/destA/labels",
            body={"action": "DELETE", "labels": [{"key": "env", "values": []}]},
        )

    def test_patch_destination_labels_http_error_propagates(self):
        mock_http = MagicMock()
        mock_http.patch.side_effect = HttpError("Not Found", status_code=404, response_text="Not Found")
        client = DestinationClient(mock_http)

        with pytest.raises(HttpError):
            client.patch_destination_labels("destA", PatchLabels(action="ADD", labels=[]), Level.SUB_ACCOUNT)
