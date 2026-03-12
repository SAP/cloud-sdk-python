"""Unit tests for Destination HTTP utilities (TokenProvider, DestinationHttp)."""

import pytest
from unittest.mock import MagicMock, patch
from requests import Response
from requests.exceptions import RequestException

from sap_cloud_sdk.destination._http import TokenProvider, DestinationHttp
from sap_cloud_sdk.destination.config import DestinationConfig
from sap_cloud_sdk.destination.exceptions import HttpError


class TestTokenProvider:

    @patch("sap_cloud_sdk.destination._http.OAuth2Session")
    def test_fetch_token(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {
            "access_token": "tok-1",
        }

        binding = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="cid",
            client_secret="csecret",
            identityzone="provider-zone",
        )
        provider = TokenProvider(binding)

        # First call should fetch
        token1 = provider.get_token()
        assert token1 == "tok-1"
        mock_session.fetch_token.assert_called_once_with(
            token_url="https://auth.example.com/oauth/token",
            client_id="cid",
            client_secret="csecret",
            include_client_id=True,
        )

        # Second call should also fetch (no caching in simple implementation)
        mock_session.fetch_token.reset_mock()
        mock_session.fetch_token.return_value = {"access_token": "tok-1"}
        token2 = provider.get_token()
        assert token2 == "tok-1"
        mock_session.fetch_token.assert_called_once_with(
            token_url="https://auth.example.com/oauth/token",
            client_id="cid",
            client_secret="csecret",
            include_client_id=True,
        )

    @patch("sap_cloud_sdk.destination._http.OAuth2Session")
    def test_missing_access_token_raises(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {
            # missing access_token
            "expires_in": 3600,
        }

        binding = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="cid",
            client_secret="csecret",
            identityzone="provider-zone",
        )
        provider = TokenProvider(binding)

        with pytest.raises(HttpError, match="missing access_token"):
            provider.get_token()

    @patch("sap_cloud_sdk.destination._http.OAuth2Session")
    def test_tenant_subdomain_replaces_identityzone(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session

        # Return different tokens per call to verify per-URL caching
        mock_session.fetch_token.side_effect = [
            {"access_token": "sub-token", "expires_in": 3600},
            {"access_token": "prov-token", "expires_in": 3600},
        ]

        binding = DestinationConfig(
            url="https://destination.example.com",
            # Include identityzone in token_url for replacement
            token_url="https://provider-zone.authentication.region/oauth/token",
            client_id="cid",
            client_secret="csecret",
            identityzone="provider-zone",
        )
        provider = TokenProvider(binding)

        # Subscriber context: replace 'provider-zone' with tenant subdomain
        sub_token = provider.get_token(tenant_subdomain="tenant-123")
        assert sub_token == "sub-token"
        mock_session.fetch_token.assert_called_with(
            token_url="https://tenant-123.authentication.region/oauth/token",
            client_id="cid",
            client_secret="csecret",
            include_client_id=True,
        )

        # Provider context: base token URL unchanged
        prov_token = provider.get_token(tenant_subdomain=None)
        assert prov_token == "prov-token"
        mock_session.fetch_token.assert_called_with(
            token_url="https://provider-zone.authentication.region/oauth/token",
            client_id="cid",
            client_secret="csecret",
            include_client_id=True,
        )


class TestDestinationHttp:

    def _make_binding(self, base_url: str = "https://destination.example.com/") -> DestinationConfig:
        return DestinationConfig(
            url=base_url,
            token_url="https://auth.example.com/oauth/token",
            client_id="cid",
            client_secret="csecret",
            identityzone="provider-zone",
        )

    def test_base_url_construction_trailing_slash_removed(self):
        binding = self._make_binding("https://destination.example.com/")
        tp = MagicMock()
        http = DestinationHttp(config=binding, token_provider=tp, session=MagicMock())
        assert http.base_url == "https://destination.example.com/destination-configuration"

        binding2 = self._make_binding("https://destination.example.com")
        http2 = DestinationHttp(config=binding2, token_provider=tp, session=MagicMock())
        assert http2.base_url == "https://destination.example.com/destination-configuration"

    def test_get_success_and_auth_header(self):
        binding = self._make_binding()
        token_provider = MagicMock()
        token_provider.get_token.return_value = "abc123"

        session = MagicMock()
        resp = MagicMock(spec=Response)
        resp.status_code = 200
        session.request.return_value = resp

        http = DestinationHttp(config=binding, token_provider=token_provider, session=session)
        result = http.get("v1/instanceDestinations/my-dest", tenant_subdomain="tenant-1")

        assert result is resp
        # Verify request call and Authorization header passed
        args, kwargs = session.request.call_args
        assert kwargs["method"] == "GET"
        assert "https://destination.example.com/destination-configuration/v1/instanceDestinations/my-dest" in kwargs["url"]
        assert kwargs["headers"]["Authorization"] == "Bearer abc123"

        token_provider.get_token.assert_called_once_with("tenant-1")

    def test_http_error_includes_status_and_text(self):
        binding = self._make_binding()
        token_provider = MagicMock()
        token_provider.get_token.return_value = "abc123"

        session = MagicMock()
        bad_resp = MagicMock(spec=Response)
        bad_resp.status_code = 404
        bad_resp.text = "Not Found"
        session.request.return_value = bad_resp

        http = DestinationHttp(config=binding, token_provider=token_provider, session=session)

        with pytest.raises(HttpError) as exc:
            http.get("instanceDestinations/unknown")

        err = exc.value
        assert err.status_code == 404
        assert "Not Found" in err.response_text  # ty: ignore[unsupported-operator]
        assert "HTTP 404 for GET" in str(err)

    def test_request_network_error_wrapped(self):
        binding = self._make_binding()
        token_provider = MagicMock()
        token_provider.get_token.return_value = "abc123"

        session = MagicMock()
        session.request.side_effect = RequestException("boom")

        http = DestinationHttp(config=binding, token_provider=token_provider, session=session)

        with pytest.raises(HttpError, match="request failed: boom"):
            http.get("any/path")
