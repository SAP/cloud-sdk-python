import pytest
from unittest.mock import MagicMock

from sap_cloud_sdk.core.dpi_ng.auth import AuthProvider, ClientCertificateAuth
from sap_cloud_sdk.core.dpi_ng.consent.config import ConsentConfig


def valid_auth():
    return MagicMock(spec=AuthProvider)


class TestDefaults:
    def test_timeout_default(self):
        cfg = ConsentConfig(base_url="https://example.com", auth=valid_auth())
        assert cfg.timeout == 30.0

    def test_verify_ssl_default(self):
        cfg = ConsentConfig(base_url="https://example.com", auth=valid_auth())
        assert cfg.verify_ssl is True

    def test_service_path_default(self):
        cfg = ConsentConfig(base_url="https://example.com", auth=valid_auth())
        assert cfg.service_path == "/sap/cp/kernel/dpi/consent/odata/v4"

    def test_tenant_id_default_is_none(self):
        cfg = ConsentConfig(base_url="https://example.com", auth=valid_auth())
        assert cfg.tenant_id is None


class TestCustomValues:
    def test_custom_timeout_stored(self):
        cfg = ConsentConfig(
            base_url="https://example.com", auth=valid_auth(), timeout=60.0
        )
        assert cfg.timeout == 60.0

    def test_verify_ssl_false_stored(self):
        cfg = ConsentConfig(
            base_url="https://example.com", auth=valid_auth(), verify_ssl=False
        )
        assert cfg.verify_ssl is False

    def test_custom_service_path_stored(self):
        cfg = ConsentConfig(
            base_url="https://example.com",
            auth=valid_auth(),
            service_path="/custom/path",
        )
        assert cfg.service_path == "/custom/path"

    def test_tenant_id_stored(self):
        cfg = ConsentConfig(
            base_url="https://example.com",
            auth=ClientCertificateAuth(cert_file="cert.pem", key_file="key.pem"),
            tenant_id="tenant-abc-123",
        )
        assert cfg.tenant_id == "tenant-abc-123"


class TestTenantId:
    def test_cert_auth_without_tenant_id_raises(self):
        with pytest.raises(ValueError, match="tenant_id is required"):
            ConsentConfig(
                base_url="https://example.com",
                auth=ClientCertificateAuth(cert_file="cert.pem", key_file="key.pem"),
            )

    def test_non_cert_auth_with_tenant_id_raises(self):
        with pytest.raises(ValueError, match="tenant_id must not be set"):
            ConsentConfig(
                base_url="https://example.com",
                auth=valid_auth(),
                tenant_id="tenant-123",
            )
