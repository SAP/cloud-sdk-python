import pytest
from unittest.mock import MagicMock

from sap_cloud_sdk.core.dpi_ng.consent.auth import AuthProvider
from sap_cloud_sdk.core.dpi_ng.consent.config import ConsentSDKConfig


def valid_auth():
    return MagicMock(spec=AuthProvider)


class TestValidConstruction:
    def test_https_url_accepted(self):
        cfg = ConsentSDKConfig(base_url="https://example.com", auth=valid_auth())
        assert cfg.base_url == "https://example.com"

    def test_http_url_accepted(self):
        cfg = ConsentSDKConfig(base_url="http://example.com", auth=valid_auth())
        assert cfg.base_url == "http://example.com"

    def test_url_with_path_accepted(self):
        cfg = ConsentSDKConfig(
            base_url="https://consent.cfapps.eu10.hana.ondemand.com",
            auth=valid_auth(),
        )
        assert "hana.ondemand.com" in cfg.base_url

    def test_trailing_slash_stripped(self):
        cfg = ConsentSDKConfig(base_url="https://example.com/", auth=valid_auth())
        assert cfg.base_url == "https://example.com"

    def test_multiple_trailing_slashes_stripped(self):
        cfg = ConsentSDKConfig(base_url="https://example.com///", auth=valid_auth())
        assert cfg.base_url == "https://example.com"

    def test_auth_stored(self):
        auth = valid_auth()
        cfg = ConsentSDKConfig(base_url="https://example.com", auth=auth)
        assert cfg.auth is auth


class TestDefaults:
    def test_timeout_default(self):
        cfg = ConsentSDKConfig(base_url="https://example.com", auth=valid_auth())
        assert cfg.timeout == 30.0

    def test_verify_ssl_default(self):
        cfg = ConsentSDKConfig(base_url="https://example.com", auth=valid_auth())
        assert cfg.verify_ssl is True

    def test_service_path_default(self):
        cfg = ConsentSDKConfig(base_url="https://example.com", auth=valid_auth())
        assert cfg.service_path == "/sap/cp/kernel/dpi/consent/odata/v4"


class TestCustomValues:
    def test_custom_timeout_stored(self):
        cfg = ConsentSDKConfig(
            base_url="https://example.com", auth=valid_auth(), timeout=60.0
        )
        assert cfg.timeout == 60.0

    def test_verify_ssl_false_stored(self):
        cfg = ConsentSDKConfig(
            base_url="https://example.com", auth=valid_auth(), verify_ssl=False
        )
        assert cfg.verify_ssl is False

    def test_custom_service_path_stored(self):
        cfg = ConsentSDKConfig(
            base_url="https://example.com",
            auth=valid_auth(),
            service_path="/custom/path",
        )
        assert cfg.service_path == "/custom/path"


class TestInvalidBaseUrl:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="base_url must be a valid HTTP"):
            ConsentSDKConfig(base_url="", auth=valid_auth())

    def test_plain_string_raises(self):
        with pytest.raises(ValueError, match="base_url must be a valid HTTP"):
            ConsentSDKConfig(base_url="not-a-url", auth=valid_auth())

    def test_ftp_scheme_raises(self):
        with pytest.raises(ValueError, match="base_url must be a valid HTTP"):
            ConsentSDKConfig(base_url="ftp://example.com", auth=valid_auth())

    def test_missing_scheme_raises(self):
        with pytest.raises(ValueError, match="base_url must be a valid HTTP"):
            ConsentSDKConfig(base_url="example.com", auth=valid_auth())

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="base_url must be a valid HTTP"):
            ConsentSDKConfig(base_url="   ", auth=valid_auth())


class TestInvalidAuth:
    def test_none_auth_raises(self):
        with pytest.raises(ValueError, match="auth must be an AuthProvider"):
            ConsentSDKConfig(base_url="https://example.com", auth=None)  # ty: ignore[invalid-argument-type]

    def test_string_auth_raises(self):
        with pytest.raises(ValueError, match="auth must be an AuthProvider"):
            ConsentSDKConfig(base_url="https://example.com", auth="Bearer token123")  # ty: ignore[invalid-argument-type]

    def test_dict_auth_raises(self):
        with pytest.raises(ValueError, match="auth must be an AuthProvider"):
            ConsentSDKConfig(
                base_url="https://example.com", auth={"token": "abc"}  # ty: ignore[invalid-argument-type]
            )

    def test_plain_object_auth_raises(self):
        with pytest.raises(ValueError, match="auth must be an AuthProvider"):
            ConsentSDKConfig(base_url="https://example.com", auth=object())  # ty: ignore[invalid-argument-type]
