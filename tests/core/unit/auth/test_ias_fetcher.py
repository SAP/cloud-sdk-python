"""Unit tests for core auth — IasTokenFetcher."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from sap_cloud_sdk.core.auth._ias_fetcher import (
    AuthError,
    IasTokenFetcher,
    _CC_CACHE_KEY,
)
from sap_cloud_sdk.core.auth._token_cache import InMemoryTokenCache


def _make_token_response(token: str = "core-access-token", expires_in: int = 3600):
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"access_token": token, "expires_in": expires_in}
    return resp


@pytest.fixture
def mock_session():
    return MagicMock(spec=requests.Session)


@pytest.fixture
def fetcher(mock_session):
    return IasTokenFetcher(
        ias_url="https://tenant.accounts.ondemand.com",
        client_id="client-id",
        client_secret="client-secret",
        session=mock_session,
    )


class TestIasTokenFetcherCore:
    def test_get_token_calls_correct_endpoint(self, fetcher, mock_session):
        mock_session.post.return_value = _make_token_response()
        token = fetcher.get_token()
        assert token == "core-access-token"
        mock_session.post.assert_called_once()
        url = mock_session.post.call_args[0][0]
        assert url == "https://tenant.accounts.ondemand.com/oauth2/token"

    def test_ias_url_trailing_slash_normalised(self, mock_session):
        fetcher = IasTokenFetcher(
            ias_url="https://tenant.accounts.ondemand.com/",
            client_id="c",
            client_secret="s",
            session=mock_session,
        )
        mock_session.post.return_value = _make_token_response()
        fetcher.get_token()
        url = mock_session.post.call_args[0][0]
        assert url == "https://tenant.accounts.ondemand.com/oauth2/token"

    def test_token_is_cached(self, fetcher, mock_session):
        mock_session.post.return_value = _make_token_response()
        t1 = fetcher.get_token()
        t2 = fetcher.get_token()
        assert t1 == t2 == "core-access-token"
        assert mock_session.post.call_count == 1

    def test_expired_token_refreshed(self, fetcher, mock_session):
        mock_session.post.return_value = _make_token_response()
        fetcher.get_token()
        fetcher._cache.set(_CC_CACHE_KEY, "stale", 0)
        t2 = fetcher.get_token()
        assert t2 == "core-access-token"
        assert mock_session.post.call_count == 2

    def test_http_error_raises_auth_error(self, fetcher, mock_session):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 401
        resp.text = "Unauthorized"
        mock_session.post.return_value = resp
        with pytest.raises(AuthError, match="401"):
            fetcher.get_token()

    def test_missing_access_token_raises_auth_error(self, fetcher, mock_session):
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {"expires_in": 3600}
        mock_session.post.return_value = resp
        with pytest.raises(AuthError, match="access_token"):
            fetcher.get_token()

    def test_network_error_raises_auth_error(self, fetcher, mock_session):
        mock_session.post.side_effect = requests.RequestException("timeout")
        with pytest.raises(AuthError, match="token request failed"):
            fetcher.get_token()

    def test_non_integer_expires_in_raises_auth_error(self, fetcher, mock_session):
        """A misbehaving proxy/IAS response with ``expires_in: "abc"`` must
        surface as ``AuthError`` rather than a raw ``ValueError``."""
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {"access_token": "tok", "expires_in": "not-a-number"}
        mock_session.post.return_value = resp
        with pytest.raises(AuthError, match="non-integer 'expires_in'"):
            fetcher.get_token()

    def test_null_expires_in_raises_auth_error(self, fetcher, mock_session):
        """``expires_in: null`` (explicit JSON null) must surface as ``AuthError``."""
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {"access_token": "tok", "expires_in": None}
        mock_session.post.return_value = resp
        with pytest.raises(AuthError, match="non-integer 'expires_in'"):
            fetcher.get_token()

    def test_exchange_token_uses_jwt_bearer_grant(self, fetcher, mock_session):
        mock_session.post.return_value = _make_token_response("obo-token")
        result = fetcher.exchange_token("user.jwt.here")
        assert result == "obo-token"
        payload = mock_session.post.call_args[1]["data"]
        assert payload["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
        assert payload["assertion"] == "user.jwt.here"

    def test_exchange_token_not_cached(self, fetcher, mock_session):
        mock_session.post.return_value = _make_token_response("obo-token")
        fetcher.exchange_token("jwt-1")
        fetcher.exchange_token("jwt-2")
        assert mock_session.post.call_count == 2

    def test_custom_cache_used(self, mock_session):
        custom = InMemoryTokenCache()
        fetcher = IasTokenFetcher(
            ias_url="https://t.accounts.ondemand.com",
            client_id="c",
            client_secret="s",
            session=mock_session,
            cache=custom,
        )
        mock_session.post.return_value = _make_token_response("tok")
        fetcher.get_token()
        assert custom.get(_CC_CACHE_KEY) == "tok"

    def test_grant_type_is_client_credentials(self, fetcher, mock_session):
        mock_session.post.return_value = _make_token_response()
        fetcher.get_token()
        payload = mock_session.post.call_args[1]["data"]
        assert payload["grant_type"] == "client_credentials"
        assert payload["client_id"] == "client-id"
        assert payload["client_secret"] == "client-secret"
