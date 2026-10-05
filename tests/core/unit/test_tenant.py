"""Unit tests for sap_cloud_sdk.core.url_utils."""

import pytest

from sap_cloud_sdk.core._tenant import _validate_tenant_subdomain, _derive_tenant_token_url


class TestValidateTenantSubdomain:

    @pytest.mark.parametrize("valid", [
        "tenant",
        "tenant-123",
        "my-company-subdomain",
        "a",
        "a" * 63,
        "A1b2C3",
        "xn--nxasmq6b",  # punycoded label — valid RFC 1123 label chars
    ])
    def test_valid_subdomains_do_not_raise(self, valid):
        _validate_tenant_subdomain(valid)  # must not raise

    @pytest.mark.parametrize("invalid, description", [
        ("", "empty string"),
        ("-leading-hyphen", "starts with hyphen"),
        ("trailing-hyphen-", "ends with hyphen"),
        ("-both-", "starts and ends with hyphen"),
        ("a" * 64, "64 chars — one over the 63-char limit"),
        ("has.dot", "dot is not a valid label char"),
        ("has space", "space is not allowed"),
        ("under_score", "underscore is not allowed"),
        ("has/slash", "slash is not allowed"),
    ])
    def test_invalid_subdomains_raise_value_error(self, invalid, description):
        with pytest.raises(ValueError, match="Invalid tenant_subdomain"):
            _validate_tenant_subdomain(invalid)

    def test_none_is_a_no_op(self):
        _validate_tenant_subdomain(None)  # must not raise


class TestDeriveTenantTokenUrl:
    BASE = "https://provider-zone.authentication.eu10.hana.ondemand.com/oauth/token"
    IZ = "provider-zone"

    def test_replaces_first_label_only(self):
        result = _derive_tenant_token_url(self.BASE, self.IZ, "tenant-123")
        assert result == "https://tenant-123.authentication.eu10.hana.ondemand.com/oauth/token"

    def test_scheme_preserved(self):
        result = _derive_tenant_token_url(self.BASE, self.IZ, "tenant-123")
        assert result.startswith("https://")

    def test_path_preserved(self):
        result = _derive_tenant_token_url(self.BASE, self.IZ, "tenant-123")
        assert result.endswith("/oauth/token")

    def test_identityzone_in_path_not_replaced(self):
        # Even if identityzone value appears in the path, it must not be touched
        url = f"https://provider-zone.auth.region/{self.IZ}/token"
        result = _derive_tenant_token_url(url, self.IZ, "tenant-abc")
        assert result == f"https://tenant-abc.auth.region/{self.IZ}/token"

    def test_port_preserved_when_present(self):
        url = "https://provider-zone.authentication.region:8443/oauth/token"
        result = _derive_tenant_token_url(url, self.IZ, "tenant-123")
        assert result == "https://tenant-123.authentication.region:8443/oauth/token"

    def test_no_match_returns_original_url(self):
        url = "https://other-zone.authentication.region/oauth/token"
        result = _derive_tenant_token_url(url, self.IZ, "tenant-123")
        assert result == url

    def test_single_label_hostname_returns_original(self):
        # token_url with no dots in host — nothing to replace
        url = "https://provider-zone/oauth/token"
        result = _derive_tenant_token_url(url, self.IZ, "tenant-123")
        assert result == url

