"""Unit tests for IasTokenFetcher."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from sap_cloud_sdk.adms._auth import IasTokenFetcher
from sap_cloud_sdk.adms.config import AdmsConfig
from sap_cloud_sdk.adms.exceptions import AuthError
from sap_cloud_sdk.core.auth._ias_fetcher import _CC_CACHE_KEY


@pytest.fixture
def config() -> AdmsConfig:
    return AdmsConfig(
        service_url="https://adm.example.com",
        ias_url="https://tenant.accounts.ondemand.com",
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


@pytest.fixture
def mock_session():
    return MagicMock(spec=requests.Session)


def _make_token_response(token: str = "my-access-token", expires_in: int = 3600):
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"access_token": token, "expires_in": expires_in}
    return resp


class TestIasTokenFetcher:
    def test_get_token_calls_ias_endpoint(self, config, mock_session):
        mock_session.post.return_value = _make_token_response()
        fetcher = IasTokenFetcher(config=config, session=mock_session)

        token = fetcher.get_token()

        assert token == "my-access-token"
        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args
        assert call_kwargs[0][0] == "https://tenant.accounts.ondemand.com/oauth2/token"
        payload = call_kwargs[1]["data"]
        assert payload["grant_type"] == "client_credentials"
        assert payload["client_id"] == "test-client-id"

    def test_token_is_cached_on_second_call(self, config, mock_session):
        mock_session.post.return_value = _make_token_response()
        fetcher = IasTokenFetcher(config=config, session=mock_session)

        t1 = fetcher.get_token()
        t2 = fetcher.get_token()

        assert t1 == t2 == "my-access-token"
        # Should only have called the token endpoint once
        assert mock_session.post.call_count == 1

    def test_expired_token_is_refreshed(self, config, mock_session):
        mock_session.post.return_value = _make_token_response()
        fetcher = IasTokenFetcher(config=config, session=mock_session)
        fetcher.get_token()  # First fetch

        # Force the cached entry to expire immediately
        fetcher._cache.set(_CC_CACHE_KEY, "stale-token", 0)

        t2 = fetcher.get_token()
        assert t2 == "my-access-token"
        assert mock_session.post.call_count == 2

    def test_http_error_raises_auth_error(self, config, mock_session):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 401
        resp.text = "Unauthorized"
        mock_session.post.return_value = resp

        fetcher = IasTokenFetcher(config=config, session=mock_session)
        with pytest.raises(AuthError, match="HTTP 401"):
            fetcher.get_token()

    def test_missing_access_token_raises_auth_error(self, config, mock_session):
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {"not_a_token": "value"}
        mock_session.post.return_value = resp

        fetcher = IasTokenFetcher(config=config, session=mock_session)
        with pytest.raises(AuthError, match="missing 'access_token'"):
            fetcher.get_token()

    def test_connection_error_raises_auth_error(self, config, mock_session):
        mock_session.post.side_effect = requests.ConnectionError("no network")

        fetcher = IasTokenFetcher(config=config, session=mock_session)
        with pytest.raises(AuthError, match="IAS token request failed"):
            fetcher.get_token()

    def test_exchange_token_uses_jwt_bearer_grant(self, config, mock_session):
        mock_session.post.return_value = _make_token_response(token="user-token")
        fetcher = IasTokenFetcher(config=config, session=mock_session)

        token = fetcher.exchange_token("user-jwt-123")

        assert token == "user-token"
        payload = mock_session.post.call_args[1]["data"]
        assert payload["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
        assert payload["assertion"] == "user-jwt-123"

    def test_exchange_token_is_not_cached(self, config, mock_session):
        mock_session.post.return_value = _make_token_response(token="user-token")
        fetcher = IasTokenFetcher(config=config, session=mock_session)

        fetcher.exchange_token("jwt-1")
        fetcher.exchange_token("jwt-2")

        # Each OBO call must hit the token endpoint
        assert mock_session.post.call_count == 2
        # In-memory cache should NOT be populated by OBO calls
        assert fetcher._cache.get(_CC_CACHE_KEY) is None

    def test_default_expiry_when_no_expires_in(self, config, mock_session):
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {"access_token": "tok"}  # no expires_in
        mock_session.post.return_value = resp

        fetcher = IasTokenFetcher(config=config, session=mock_session)
        token = fetcher.get_token()
        assert token == "tok"
        assert fetcher._cache.get(_CC_CACHE_KEY) is not None
