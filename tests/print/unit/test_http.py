"""Unit tests for Print HTTP transport and TokenProvider."""

import base64
import json
import pytest
from unittest.mock import MagicMock, patch

from sap_cloud_sdk.print._http import TokenProvider
from sap_cloud_sdk.print.config import PrintConfig
from sap_cloud_sdk.print.exceptions import HttpError


def _make_jwt(claims: dict) -> str:
    """Build a minimal unsigned JWT with the given claims."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = (
        base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    )
    return f"{header}.{payload}."


def _config() -> PrintConfig:
    return PrintConfig(
        url="https://api.eu10.print.services.sap",
        token_url="https://tenant.authentication.eu10.hana.ondemand.com/oauth/token",
        client_id="client-id",
        client_secret="client-secret",
    )


class TestTokenProvider:
    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_returns_access_token(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "tok-abc"}

        provider = TokenProvider(_config())
        assert provider.get_token() == "tok-abc"

    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_missing_access_token_raises(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {"expires_in": 3600}

        provider = TokenProvider(_config())
        with pytest.raises(HttpError, match="missing access_token"):
            provider.get_token()

    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_resolve_username_returns_user_name_claim(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {
            "access_token": _make_jwt(
                {"user_name": "john.doe@example.com", "client_id": "sb-app"}
            )
        }

        provider = TokenProvider(_config())
        assert provider.resolve_username() == "john.doe@example.com"

    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_resolve_username_falls_back_to_client_id_claim(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {
            "access_token": _make_jwt({"client_id": "sb-app!t123"})
        }

        provider = TokenProvider(_config())
        assert provider.resolve_username() == "sb-app!t123"

    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_resolve_username_falls_back_to_config_client_id_on_bad_token(
        self, mock_oauth
    ):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "not.a.jwt"}

        provider = TokenProvider(_config())
        assert provider.resolve_username() == "client-id"

    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_resolve_username_uses_cached_token(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {
            "access_token": _make_jwt({"user_name": "cached@example.com"})
        }

        provider = TokenProvider(_config())
        provider.get_token()
        # fetch_token should not be called again
        mock_session.fetch_token.reset_mock()
        assert provider.resolve_username() == "cached@example.com"
        mock_session.fetch_token.assert_not_called()


class TestTokenProviderFetchFailure:
    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_fetch_token_exception_raises_http_error(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.side_effect = Exception(
            "(invalid_client) Bad credentials"
        )

        provider = TokenProvider(_config())
        with pytest.raises(HttpError, match="failed to acquire token"):
            provider.get_token()


class TestTokenProviderRotation:
    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_proactive_rotation_rebuilds_session_when_binding_changed(self, mock_oauth):
        new_config = PrintConfig(
            url="https://api.eu10.print.services.sap",
            token_url="https://new-tenant.authentication.eu10.hana.ondemand.com/oauth/token",
            client_id="new-client-id",
            client_secret="new-client-secret",
        )
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "tok-v2"}

        mock_factory = MagicMock(return_value=new_config)
        mock_factory.has_changed = MagicMock(return_value=True)

        provider = TokenProvider(mock_factory)
        # has_changed() is True: provider must re-read config before fetching
        token = provider.get_token()

        assert token == "tok-v2"
        assert provider._config is new_config
        # factory called once at init, once on rotation
        assert mock_factory.call_count == 2

    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_no_rebuild_when_binding_unchanged(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "tok-same"}

        mock_factory = MagicMock(return_value=_config())
        mock_factory.has_changed = MagicMock(return_value=False)

        provider = TokenProvider(mock_factory)
        init_session = provider._session

        provider.get_token()

        mock_factory.has_changed.assert_called_once()
        assert provider._session is init_session  # no rebuild
        assert mock_factory.call_count == 1  # no extra factory call

    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_static_config_has_no_has_changed_check(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "tok-static"}

        provider = TokenProvider(_config())
        init_session = provider._session

        provider.get_token()

        # no has_changed() — session stays the same
        assert provider._session is init_session
