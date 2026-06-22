"""Unit tests for Print HTTP transport and TokenProvider."""

import base64
import json
import pytest
from unittest.mock import MagicMock, patch
from requests.exceptions import RequestException

from sap_cloud_sdk.print._http import TokenProvider, PrintHttp
from sap_cloud_sdk.print.config import PrintConfig
from sap_cloud_sdk.print.exceptions import HttpError


def _make_jwt(claims: dict) -> str:
    """Build a minimal unsigned JWT with the given claims."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
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
            "access_token": _make_jwt({"user_name": "john.doe@example.com", "client_id": "sb-app"})
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
    def test_resolve_username_falls_back_to_config_client_id_on_bad_token(self, mock_oauth):
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


class TestPrintHttp:

    def _http(self, mock_session) -> PrintHttp:
        config = _config()
        mock_tp = MagicMock()
        mock_tp.get_token.return_value = "test-token"
        return PrintHttp(config=config, token_provider=mock_tp, session=mock_session)

    def _ok_response(self, status_code: int = 200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = ""
        return resp

    def _error_response(self, status_code: int):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = "error body"
        return resp

    def test_get_constructs_correct_url(self):
        mock_session = MagicMock()
        mock_session.request.return_value = self._ok_response()

        http = self._http(mock_session)
        http.get("qm/api/v1/rest/queues")

        _, kwargs = mock_session.request.call_args
        assert "print.services.sap" in kwargs["url"]
        assert "queues" in kwargs["url"]
        assert kwargs["method"] == "GET"

    def test_authorization_header_set(self):
        mock_session = MagicMock()
        mock_session.request.return_value = self._ok_response()

        http = self._http(mock_session)
        http.get("some/path")

        _, kwargs = mock_session.request.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test-token"

    def test_non_2xx_raises_http_error(self):
        mock_session = MagicMock()
        mock_session.request.return_value = self._error_response(500)

        http = self._http(mock_session)
        with pytest.raises(HttpError) as exc_info:
            http.get("some/path")
        assert exc_info.value.status_code == 500

    def test_request_exception_raises_http_error(self):
        mock_session = MagicMock()
        mock_session.request.side_effect = RequestException("connection refused")

        http = self._http(mock_session)
        with pytest.raises(HttpError, match="request failed"):
            http.get("some/path")

    def test_put_sends_json_body(self):
        mock_session = MagicMock()
        mock_session.request.return_value = self._ok_response(204)

        http = self._http(mock_session)
        http.put("some/path", json={"key": "value"})

        _, kwargs = mock_session.request.call_args
        assert kwargs["json"] == {"key": "value"}
        assert kwargs["method"] == "PUT"

    def test_post_multipart_sends_files(self):
        mock_session = MagicMock()
        mock_session.request.return_value = self._ok_response(201)

        http = self._http(mock_session)
        http.post("some/path", files={"file": ("doc.pdf", b"data")})

        _, kwargs = mock_session.request.call_args
        assert kwargs["files"] is not None
        assert kwargs["method"] == "POST"

    def test_extra_headers_merged_into_request(self):
        mock_session = MagicMock()
        mock_session.request.return_value = self._ok_response()

        http = self._http(mock_session)
        http.get("some/path", headers={"X-Custom": "value"})

        _, kwargs = mock_session.request.call_args
        assert kwargs["headers"]["X-Custom"] == "value"
        assert kwargs["headers"]["Authorization"] == "Bearer test-token"

    def test_response_text_read_failure_still_raises_http_error(self):
        mock_session = MagicMock()
        resp = MagicMock()
        resp.status_code = 500
        type(resp).text = property(lambda self: (_ for _ in ()).throw(RuntimeError("unreadable")))
        mock_session.request.return_value = resp

        http = self._http(mock_session)
        with pytest.raises(HttpError) as exc_info:
            http.get("some/path")
        assert exc_info.value.status_code == 500

    def test_get_username_delegates_to_token_provider(self):
        mock_session = MagicMock()
        config = _config()
        mock_tp = MagicMock()
        mock_tp.resolve_username.return_value = "user@example.com"
        http = PrintHttp(config=config, token_provider=mock_tp, session=mock_session)

        assert http.get_username() == "user@example.com"
        mock_tp.resolve_username.assert_called_once()


class TestTokenProviderFetchFailure:

    @patch("sap_cloud_sdk.print._http.OAuth2Session")
    def test_fetch_token_exception_raises_http_error(self, mock_oauth):
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.side_effect = Exception("(invalid_client) Bad credentials")

        provider = TokenProvider(_config())
        with pytest.raises(HttpError, match="failed to acquire token"):
            provider.get_token()
