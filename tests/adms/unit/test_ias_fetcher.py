"""Unit tests for IasTokenFetcher."""

from unittest.mock import MagicMock

import pytest
import requests

from sap_cloud_sdk.adms._ias_fetcher import (
    IasTokenFetcher,
    _CC_CACHE_KEY,
)
from sap_cloud_sdk.adms._token_cache import InMemoryTokenCache
from sap_cloud_sdk.adms.config import AdmsConfig
from sap_cloud_sdk.adms.exceptions import AuthError


def _make_token_response(token: str = "core-access-token", expires_in: int = 3600):
    resp = MagicMock()
    resp.ok = True
    resp.json.return_value = {"access_token": token, "expires_in": expires_in}
    return resp


def _make_config(
    ias_url: str = "https://tenant.accounts.ondemand.com",
    client_id: str = "client-id",
    client_secret: str = "client-secret",
) -> AdmsConfig:
    return AdmsConfig(
        service_url="https://adm.example.com",
        ias_url=ias_url,
        client_id=client_id,
        client_secret=client_secret,
    )


@pytest.fixture
def config() -> AdmsConfig:
    return _make_config()


@pytest.fixture
def mock_session():
    return MagicMock(spec=requests.Session)


@pytest.fixture
def fetcher(config, mock_session):
    return IasTokenFetcher(config=config, session=mock_session)


class TestIasTokenFetcherCore:
    def test_get_token_calls_correct_endpoint(self, fetcher, mock_session):
        mock_session.post.return_value = _make_token_response()
        token = fetcher.get_token()
        assert token == "core-access-token"
        mock_session.post.assert_called_once()
        url = mock_session.post.call_args[0][0]
        assert url == "https://tenant.accounts.ondemand.com/oauth2/token"

    def test_ias_url_trailing_slash_normalised(self, mock_session):
        config = _make_config(ias_url="https://tenant.accounts.ondemand.com/")
        fetcher = IasTokenFetcher(config=config, session=mock_session)
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

    def test_default_expiry_when_no_expires_in(self, fetcher, mock_session):
        """An IAS response that omits ``expires_in`` entirely must fall back to
        the default TTL and still cache the token."""
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {"access_token": "tok"}  # no expires_in
        mock_session.post.return_value = resp
        token = fetcher.get_token()
        assert token == "tok"
        assert fetcher._cache.get(_CC_CACHE_KEY) == "tok"

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
        # In-memory cache must not be populated by OBO calls.
        assert fetcher._cache.get(_CC_CACHE_KEY) is None

    def test_custom_cache_used(self, config, mock_session):
        custom = InMemoryTokenCache()
        fetcher = IasTokenFetcher(config=config, session=mock_session, cache=custom)
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

    def test_obo_and_cc_caches_are_isolated(self, fetcher, mock_session):
        """Interleaving ``get_token`` (cached) with ``exchange_token`` (not cached)
        must not collide on a shared cache key.

        Why: OBO tokens are scoped to a specific end-user JWT; sharing them
        across users would be a privilege boundary violation.  CC tokens are
        the application's own credential and should be cached for reuse.
        A naive single-key cache would either leak OBO tokens to CC callers
        or cache-bust CC on every OBO call.
        """
        mock_session.post.side_effect = [
            _make_token_response("cc-token"),  # first get_token → IAS hit
            _make_token_response("obo-token-a"),  # exchange_token(jwt_a) → IAS hit
            _make_token_response("obo-token-b"),  # exchange_token(jwt_b) → IAS hit
        ]

        cc1 = fetcher.get_token()
        obo_a = fetcher.exchange_token("jwt-a")
        cc2 = fetcher.get_token()  # must hit cache → no extra IAS call
        obo_b = fetcher.exchange_token("jwt-b")

        assert cc1 == cc2 == "cc-token"
        assert obo_a == "obo-token-a"
        assert obo_b == "obo-token-b"
        # 1 CC fetch (cached on second call) + 2 OBO fetches (never cached) = 3.
        assert mock_session.post.call_count == 3

        cc_grant_calls = [
            call
            for call in mock_session.post.call_args_list
            if call[1]["data"]["grant_type"] == "client_credentials"
        ]
        assert len(cc_grant_calls) == 1
