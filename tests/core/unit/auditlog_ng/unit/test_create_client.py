"""Tests for create_client factory function."""

import pytest
from unittest.mock import patch, Mock

from sap_cloud_sdk.core.auditlog_ng import create_client, AuditClient
from sap_cloud_sdk.core.auditlog_ng.config import AuditLogNGConfig, SCHEMA_URL
from sap_cloud_sdk.core.auditlog_ng.exceptions import ClientCreationError


class TestCreateClient:

    @patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_create_client_with_config(self, mock_provider_cls, mock_exporter_fn):
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        config = AuditLogNGConfig(
            endpoint="localhost:4317",
            deployment_id="dep-1",
            namespace="ns-1",
            insecure=True,
        )

        client = create_client(config=config)

        assert isinstance(client, AuditClient)

    @patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_create_client_with_keyword_args(self, mock_provider_cls, mock_exporter_fn):
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        client = create_client(
            endpoint="localhost:4317",
            deployment_id="dep-1",
            namespace="ns-1",
            insecure=True,
        )

        assert isinstance(client, AuditClient)

    def test_create_client_missing_endpoint_raises(self):
        with pytest.raises(ValueError, match="endpoint, deployment_id, and namespace are required"):
            create_client(deployment_id="dep-1", namespace="ns-1")

    def test_create_client_missing_deployment_id_raises(self):
        with pytest.raises(ValueError, match="endpoint, deployment_id, and namespace are required"):
            create_client(endpoint="localhost:4317", namespace="ns-1")

    def test_create_client_missing_namespace_raises(self):
        with pytest.raises(ValueError, match="endpoint, deployment_id, and namespace are required"):
            create_client(endpoint="localhost:4317", deployment_id="dep-1")

    def test_create_client_no_args_raises(self):
        with pytest.raises(ValueError, match="endpoint, deployment_id, and namespace are required"):
            create_client()

    def test_create_client_invalid_deployment_id_raises(self):
        with pytest.raises(ValueError, match="deployment_id"):
            create_client(
                endpoint="localhost:4317",
                deployment_id="bad value",
                namespace="ns-1",
            )

    @patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_create_client_unexpected_exception_wraps_in_client_creation_error(
        self, mock_provider_cls, mock_exporter_fn
    ):
        mock_provider_cls.side_effect = RuntimeError("Unexpected failure")

        with pytest.raises(ClientCreationError, match="Failed to create audit log NG client"):
            create_client(
                endpoint="localhost:4317",
                deployment_id="dep-1",
                namespace="ns-1",
                insecure=True,
            )

    @patch("sap_cloud_sdk.core.auditlog_ng.client._create_log_exporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_config_keyword_args_are_forwarded(self, mock_provider_cls, mock_exporter_fn):
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        client = create_client(
            endpoint="audit.example.com:443",
            deployment_id="dep-1",
            namespace="ns-1",
            service_name="my-svc",
            batch=True,
            compression=False,
            insecure=True,
        )

        assert client._config.service_name == "my-svc"
        assert client._config.batch is True
        assert client._config.compression is False
