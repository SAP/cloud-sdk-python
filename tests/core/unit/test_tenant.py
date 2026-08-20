"""Unit tests for sap_cloud_sdk.core.url_utils."""

import pytest

from sap_cloud_sdk.core._tenant import _validate_tenant_subdomain


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
