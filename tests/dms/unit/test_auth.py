"""Unit tests for sap_cloud_sdk.dms._auth.Auth."""

import pytest
from unittest.mock import patch

from sap_cloud_sdk.dms._auth import Auth, _MAX_CACHE_SIZE
from sap_cloud_sdk.dms.model import DMSCredentials


def _make_credentials(identityzone: str = "provider-zone") -> DMSCredentials:
    return DMSCredentials(
        uri="https://dms.example.com",
        token_url=f"https://{identityzone}.authentication.region",
        client_id="cid",
        client_secret="csecret",
        identityzone=identityzone,
    )


class TestResolveTokenUrl:
    def test_no_subdomain_returns_provider_url(self):
        creds = _make_credentials()
        auth = Auth(creds)
        assert auth._resolve_token_url(None) == creds.token_url
        assert auth._resolve_token_url("") == creds.token_url

    def test_valid_subdomain_replaces_identityzone(self):
        creds = _make_credentials()
        auth = Auth(creds)
        result = auth._resolve_token_url("tenant-123")
        assert result == "https://tenant-123.authentication.region"

    def test_invalid_subdomain_raises_value_error(self):
        creds = _make_credentials()
        auth = Auth(creds)
        with pytest.raises(ValueError, match="Invalid tenant_subdomain"):
            auth._resolve_token_url("-bad")
        with pytest.raises(ValueError, match="Invalid tenant_subdomain"):
            auth._resolve_token_url("has.dot")

    @patch("sap_cloud_sdk.dms._auth._validate_tenant_subdomain")
    def test_resolve_token_url_calls_validator(self, mock_validate):
        creds = _make_credentials()
        auth = Auth(creds)

        auth._resolve_token_url("tenant-abc")
        mock_validate.assert_called_once_with("tenant-abc")

    @patch("sap_cloud_sdk.dms._auth._validate_tenant_subdomain")
    def test_validator_not_called_when_no_subdomain(self, mock_validate):
        creds = _make_credentials()
        auth = Auth(creds)

        auth._resolve_token_url(None)
        auth._resolve_token_url("")
        mock_validate.assert_not_called()


class TestGetToken:
    def test_returns_token(self):
        creds = _make_credentials()
        auth = Auth(creds)
        with patch.object(
            auth,
            "_fetch_token",
            return_value={"access_token": "tok-1", "expires_in": 3600},
        ):
            assert auth.get_token() == "tok-1"

    def test_caches_token_on_second_call(self):
        creds = _make_credentials()
        auth = Auth(creds)
        with patch.object(
            auth,
            "_fetch_token",
            return_value={"access_token": "tok-1", "expires_in": 3600},
        ) as mock_fetch:
            auth.get_token()
            auth.get_token()
            mock_fetch.assert_called_once()

    def test_subscriber_and_provider_cached_separately(self):
        creds = _make_credentials()
        auth = Auth(creds)
        with patch.object(
            auth,
            "_fetch_token",
            side_effect=[
                {"access_token": "prov-tok", "expires_in": 3600},
                {"access_token": "sub-tok", "expires_in": 3600},
            ],
        ) as mock_fetch:
            prov = auth.get_token()
            sub = auth.get_token(tenant_subdomain="tenant-x")
            assert prov == "prov-tok"
            assert sub == "sub-tok"
            assert mock_fetch.call_count == 2

    def test_invalid_subdomain_raises_before_fetch(self):
        creds = _make_credentials()
        auth = Auth(creds)
        with patch.object(
            auth,
            "_fetch_token",
            return_value={"access_token": "tok", "expires_in": 3600},
        ) as mock_fetch:
            with pytest.raises(ValueError, match="Invalid tenant_subdomain"):
                auth.get_token(tenant_subdomain="-invalid")
            mock_fetch.assert_not_called()

    def test_cache_evicts_oldest_when_full(self):
        creds = _make_credentials()
        auth = Auth(creds)
        side_effects = [
            {"access_token": f"tok-{i}", "expires_in": 3600}
            for i in range(_MAX_CACHE_SIZE + 1)
        ]
        with patch.object(auth, "_fetch_token", side_effect=side_effects):
            for i in range(_MAX_CACHE_SIZE):
                auth.get_token(tenant_subdomain=f"tenant-{i:02d}")

            assert len(auth._cache) == _MAX_CACHE_SIZE
            assert "tenant-00" in auth._cache

            # One more entry should evict the oldest (tenant-00)
            auth.get_token(tenant_subdomain="tenant-99")
            assert len(auth._cache) == _MAX_CACHE_SIZE
            assert "tenant-00" not in auth._cache
            assert "tenant-99" in auth._cache
