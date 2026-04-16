"""Tests for configuration and validation."""

import pytest

from sap_cloud_sdk.auditlog_ng.config import (
    AuditLogNGConfig,
    SCHEMA_URL,
    _validate_source_arg,
)


class TestValidateSourceArg:

    def test_valid_alphanumeric(self):
        _validate_source_arg("abc123", "test")

    def test_valid_with_dots_dashes_underscores(self):
        _validate_source_arg("my-deployment_v1.0", "test")

    def test_valid_with_slashes_and_tildes(self):
        _validate_source_arg("sap/als~v2", "test")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="test"):
            _validate_source_arg("bad value", "test")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="test"):
            _validate_source_arg("", "test")

    def test_rejects_special_characters(self):
        with pytest.raises(ValueError, match="test"):
            _validate_source_arg("value@#!", "test")


class TestAuditLogNGConfig:

    def test_valid_minimal_config(self):
        config = AuditLogNGConfig(
            endpoint="localhost:4317",
            deployment_id="my-deployment",
            namespace="sap.als",
        )
        assert config.endpoint == "localhost:4317"
        assert config.deployment_id == "my-deployment"
        assert config.namespace == "sap.als"
        assert config.insecure is False
        assert config.batch is False
        assert config.compression is True
        assert config.service_name == "audit-client"
        assert config.schema_url == SCHEMA_URL

    def test_valid_full_config(self):
        config = AuditLogNGConfig(
            endpoint="audit.example.com:443",
            deployment_id="us30-staging",
            namespace="sap.als",
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem",
            ca_file="/path/to/ca.pem",
            insecure=False,
            service_name="my-agent",
            batch=True,
            compression=False,
            schema_url="https://custom.schema/url",
        )
        assert config.cert_file == "/path/to/cert.pem"
        assert config.key_file == "/path/to/key.pem"
        assert config.ca_file == "/path/to/ca.pem"
        assert config.service_name == "my-agent"
        assert config.batch is True
        assert config.compression is False
        assert config.schema_url == "https://custom.schema/url"

    def test_empty_endpoint_raises(self):
        with pytest.raises(ValueError, match="endpoint is required"):
            AuditLogNGConfig(
                endpoint="",
                deployment_id="my-deployment",
                namespace="sap.als",
            )

    def test_invalid_deployment_id_raises(self):
        with pytest.raises(ValueError, match="deployment_id"):
            AuditLogNGConfig(
                endpoint="localhost:4317",
                deployment_id="bad value",
                namespace="sap.als",
            )

    def test_invalid_namespace_raises(self):
        with pytest.raises(ValueError, match="namespace"):
            AuditLogNGConfig(
                endpoint="localhost:4317",
                deployment_id="my-deployment",
                namespace="bad value",
            )

    def test_defaults_for_optional_fields(self):
        config = AuditLogNGConfig(
            endpoint="localhost:4317",
            deployment_id="dep",
            namespace="ns",
        )
        assert config.cert_file is None
        assert config.key_file is None
        assert config.ca_file is None
        assert config.insecure is False
