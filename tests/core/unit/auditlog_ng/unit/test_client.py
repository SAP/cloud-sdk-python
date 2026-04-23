"""Tests for AuditClient."""
from __future__ import annotations

import json
from typing import TypedDict, Unpack
from unittest.mock import MagicMock, Mock, patch

import pytest

from sap_cloud_sdk.core.auditlog_ng.client import AuditClient
from sap_cloud_sdk.core.auditlog_ng.config import AuditLogNGConfig, SCHEMA_URL
from sap_cloud_sdk.core.auditlog_ng.exceptions import ValidationError


class ConfigKwargs(TypedDict, total=False):
    endpoint: str
    deployment_id: str
    namespace: str
    insecure: bool
    service_name: str
    cert_file: str | None
    key_file: str | None
    ca_file: str | None
    batch: bool
    compression: bool
    schema_url: str


def _make_config(**overrides: Unpack[ConfigKwargs]) -> AuditLogNGConfig:
    defaults: ConfigKwargs = {
        "endpoint": "localhost:4317",
        "deployment_id": "deployment-123",
        "namespace": "namespace-123",
        "insecure": True,
    }
    defaults.update(overrides)  # ty: ignore[invalid-argument-type]
    return AuditLogNGConfig(**defaults)


@patch("sap_cloud_sdk.core.auditlog_ng.client.OTLPLogExporter")
@patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
def _make_mocked_client(mock_provider_cls, mock_exporter_cls, *, validate_side_effect=None):
    mock_logger = Mock()
    mock_provider = Mock()
    mock_provider.get_logger.return_value = mock_logger
    mock_provider_cls.return_value = mock_provider

    config = _make_config()
    client = AuditClient(config)

    validate_patcher = patch(
        "sap_cloud_sdk.core.auditlog_ng.client.protovalidate.validate",
        side_effect=validate_side_effect,
    )
    mock_validate = validate_patcher.start()

    return client, mock_logger, mock_provider, mock_validate, validate_patcher, mock_provider_cls


def _make_mock_event(tenant_id="tenant-123", descriptor_name="DataAccess"):
    event = MagicMock()
    event.common.tenant_id = tenant_id
    event.DESCRIPTOR.name = descriptor_name
    event.SerializeToString.return_value = b"\x00\x01\x02"
    return event


class TestAuditClientInit:

    @patch("sap_cloud_sdk.core.auditlog_ng.client.OTLPLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_creates_insecure_client(self, mock_provider_cls, mock_exporter_cls):
        config = _make_config(insecure=True)
        client = AuditClient(config)

        assert client._closed is False
        mock_exporter_cls.assert_called_once()
        _, kwargs = mock_exporter_cls.call_args
        assert kwargs["insecure"] is True

    @patch("sap_cloud_sdk.core.auditlog_ng.client.OTLPLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_sets_schema_url_on_logger(self, mock_provider_cls, mock_exporter_cls):
        mock_provider = Mock()
        mock_provider.get_logger.return_value = Mock()
        mock_provider_cls.return_value = mock_provider

        config = _make_config()
        AuditClient(config)

        mock_provider.get_logger.assert_called_once()
        _, kwargs = mock_provider.get_logger.call_args
        assert kwargs["schema_url"] == SCHEMA_URL

    @patch("sap_cloud_sdk.core.auditlog_ng.client.OTLPLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_sets_resource_attributes(self, mock_provider_cls, mock_exporter_cls):
        config = _make_config(service_name="my-svc")
        AuditClient(config)

        call_kwargs = mock_provider_cls.call_args[1]
        resource = call_kwargs["resource"]
        attrs = dict(resource.attributes)
        assert attrs["service.name"] == "my-svc"
        assert attrs["sap.ucl.deployment_id"] == "deployment-123"
        assert attrs["sap.ucl.system_namespace"] == "namespace-123"


class TestAuditClientSend:

    def test_send_binary_success(self):
        client, mock_logger, _, mock_validate, patcher, _ = _make_mocked_client()
        try:
            event = _make_mock_event()
            event_id = client.send(event, "DataAccess")

            assert isinstance(event_id, str)
            mock_validate.assert_called_once_with(event)
            mock_logger.emit.assert_called_once()

            _, kwargs = mock_logger.emit.call_args
            assert kwargs["event_name"] == "sap.als.AuditEvent.DataAccess.v2"
            assert kwargs["body"] == b"\x00\x01\x02"
            assert kwargs["attributes"]["sap.auditlogging.mime_type"] == "application/protobuf"
            assert kwargs["attributes"]["sap.tenancy.tenant_id"] == "tenant-123"
            assert "cloudevents.event_id" in kwargs["attributes"]
        finally:
            patcher.stop()

    def test_send_json_success(self):
        client, mock_logger, _, mock_validate, patcher, _ = _make_mocked_client()
        try:
            event = _make_mock_event()
            event_id = client.send_json(event, "DataAccess")

            assert isinstance(event_id, str)
            mock_logger.emit.assert_called_once()

            _, kwargs = mock_logger.emit.call_args
            assert kwargs["attributes"]["sap.auditlogging.mime_type"] == "application/json"
            assert isinstance(kwargs["body"], str)
        finally:
            patcher.stop()

    def test_send_uses_descriptor_name_when_event_type_missing(self):
        client, mock_logger, _, _, patcher, _ = _make_mocked_client()
        try:
            event = _make_mock_event(descriptor_name="ConfigurationChange")
            client.send(event)

            _, kwargs = mock_logger.emit.call_args
            assert kwargs["event_name"] == "sap.als.AuditEvent.ConfigurationChange.v2"
        finally:
            patcher.stop()

    def test_send_on_closed_client_raises(self):
        client, _, _, _, patcher, _ = _make_mocked_client()
        patcher.stop()
        client.close()

        with pytest.raises(RuntimeError, match="Client is closed"):
            client.send(_make_mock_event(), "DataAccess")

    def test_send_invalid_format_raises(self):
        client, _, _, _, patcher, _ = _make_mocked_client()
        try:
            with pytest.raises(ValueError, match="format must be"):
                client.send(_make_mock_event(), "DataAccess", format="xml")
        finally:
            patcher.stop()

    def test_send_validation_failure_raises_validation_error(self):
        from protovalidate import ValidationError as ProtoValidationError

        client, mock_logger, _, _, patcher, _ = _make_mocked_client(
            validate_side_effect=ProtoValidationError("bad event", [])
        )
        try:
            with pytest.raises(ValidationError, match="Audit event validation failed"):
                client.send(_make_mock_event(), "DataAccess")

            mock_logger.emit.assert_not_called()
        finally:
            patcher.stop()

    def test_send_invalid_tenant_id_raises(self):
        client, mock_logger, _, _, patcher, _ = _make_mocked_client()
        try:
            event = _make_mock_event(tenant_id="bad tenant id")

            with pytest.raises(ValueError):
                client.send(event, "DataAccess")

            mock_logger.emit.assert_not_called()
        finally:
            patcher.stop()


class TestAuditClientLifecycle:

    def test_flush(self):
        client, _, mock_provider, _, patcher, _ = _make_mocked_client()
        patcher.stop()

        client.flush()
        mock_provider.force_flush.assert_called_once()

    def test_flush_on_closed_client_is_noop(self):
        client, _, mock_provider, _, patcher, _ = _make_mocked_client()
        patcher.stop()
        client.close()

        mock_provider.force_flush.reset_mock()
        client.flush()
        mock_provider.force_flush.assert_not_called()

    def test_close(self):
        client, _, mock_provider, _, patcher, _ = _make_mocked_client()
        patcher.stop()

        client.close()
        assert client._closed is True
        mock_provider.shutdown.assert_called_once()

    def test_context_manager(self):
        client, _, mock_provider, _, patcher, _ = _make_mocked_client()
        patcher.stop()

        with client:
            assert client._closed is False

        assert client._closed is True
        mock_provider.shutdown.assert_called_once()
