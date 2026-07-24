"""Tests for AuditClient."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict, Unpack
from unittest.mock import MagicMock, Mock, patch

import pytest

from sap_cloud_sdk.core.auditlog_ng.client import AuditClient, _fill_common_from_auth_context
from sap_cloud_sdk.core.auditlog_ng.config import AuditLogNGConfig, SCHEMA_URL
from sap_cloud_sdk.core.auditlog_ng.exceptions import ValidationError
from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import auditevent_pb2 as pb
from sap_cloud_sdk.core.telemetry import Module, Operation
from sap_cloud_sdk.ias._context import set_auth_context


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
    defaults.update(overrides)
    return AuditLogNGConfig(**defaults)


@patch("sap_cloud_sdk.core.auditlog_ng.client.GRPCLogExporter")
@patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
def _make_mocked_client(
    mock_provider_cls, mock_exporter_cls, *, validate_side_effect=None
):
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

    return (
        client,
        mock_logger,
        mock_provider,
        mock_validate,
        validate_patcher,
        mock_provider_cls,
    )


def _make_mock_event(tenant_id="tenant-123", descriptor_full_name="sap.auditlog.auditevent.v2.DataAccess"):
    event = MagicMock()
    event.common.tenant_id = tenant_id
    event.DESCRIPTOR.full_name = descriptor_full_name
    event.SerializeToString.return_value = b"\x00\x01\x02"
    return event


class TestAuditClientInit:
    @patch("sap_cloud_sdk.core.auditlog_ng.client.GRPCLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_creates_insecure_client(self, mock_provider_cls, mock_exporter_cls):
        config = _make_config(insecure=True)
        client = AuditClient(config)

        assert client._closed is False
        mock_exporter_cls.assert_called_once()
        _, kwargs = mock_exporter_cls.call_args
        assert kwargs["insecure"] is True

    @patch("sap_cloud_sdk.core.auditlog_ng.client.GRPCLogExporter")
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

    @patch("sap_cloud_sdk.core.auditlog_ng.client.GRPCLogExporter")
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

    @patch("sap_cloud_sdk.core.auditlog_ng.client.GRPCLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_init_records_create_client_metric(
        self, mock_provider_cls, mock_exporter_cls
    ):
        config = _make_config()

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
        ) as mock_metric:
            AuditClient(config)

        mock_metric.assert_called_once_with(
            Module.AUDITLOG_NG,
            None,
            Operation.AUDITLOG_CREATE_CLIENT,
            False,
        )

    @patch("sap_cloud_sdk.core.auditlog_ng.client.GRPCLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_init_records_error_metric_on_failure(
        self, mock_provider_cls, mock_exporter_cls
    ):
        mock_provider_cls.side_effect = RuntimeError("provider failed")
        config = _make_config()

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_error_metric"
        ) as mock_error_metric:
            with pytest.raises(RuntimeError, match="provider failed"):
                AuditClient(config, _telemetry_source=Module.DMS)

        mock_error_metric.assert_called_once_with(
            Module.AUDITLOG_NG,
            Module.DMS,
            Operation.AUDITLOG_CREATE_CLIENT,
            False,
        )


class TestAuditClientSend:
    def test_send_binary_success(self):
        client, mock_logger, _, mock_validate, patcher, _ = _make_mocked_client()
        try:
            event = _make_mock_event()
            event_id = client.send(event)

            assert isinstance(event_id, str)
            mock_validate.assert_called_once_with(event)
            mock_logger.emit.assert_called_once()

            _, kwargs = mock_logger.emit.call_args
            assert kwargs["event_name"] == "sap.auditlog.auditevent.v2.DataAccess"
            assert kwargs["body"] == b"\x00\x01\x02"
            assert (
                kwargs["attributes"]["sap.auditlogging.mime_type"]
                == "application/protobuf"
            )
            assert kwargs["attributes"]["sap.tenancy.tenant_id"] == "tenant-123"
            assert "cloudevents.event_id" in kwargs["attributes"]
        finally:
            patcher.stop()

    def test_send_json_success(self):
        client, mock_logger, _, mock_validate, patcher, _ = _make_mocked_client()
        try:
            event = _make_mock_event()
            event_id = client.send_json(event)

            assert isinstance(event_id, str)
            mock_logger.emit.assert_called_once()

            _, kwargs = mock_logger.emit.call_args
            assert (
                kwargs["attributes"]["sap.auditlogging.mime_type"] == "application/json"
            )
            assert isinstance(kwargs["body"], str)
        finally:
            patcher.stop()

    def test_send_uses_descriptor_name_when_event_type_missing(self):
        client, mock_logger, _, _, patcher, _ = _make_mocked_client()
        try:
            event = _make_mock_event(descriptor_full_name="sap.auditlog.auditevent.v2.ConfigurationChange")
            client.send(event)

            _, kwargs = mock_logger.emit.call_args
            assert kwargs["event_name"] == "sap.auditlog.auditevent.v2.ConfigurationChange"
        finally:
            patcher.stop()

    def test_send_on_closed_client_raises(self):
        client, _, _, _, patcher, _ = _make_mocked_client()
        patcher.stop()
        client.close()

        with pytest.raises(RuntimeError, match="Client is closed"):
            client.send(_make_mock_event())

    def test_send_invalid_format_raises(self):
        client, _, _, _, patcher, _ = _make_mocked_client()
        try:
            with pytest.raises(ValueError, match="format must be"):
                client.send(_make_mock_event(), format="xml")
        finally:
            patcher.stop()

    def test_send_validation_failure_raises_validation_error(self):
        from protovalidate import ValidationError as ProtoValidationError

        client, mock_logger, _, _, patcher, _ = _make_mocked_client(
            validate_side_effect=ProtoValidationError("bad event", [])
        )
        try:
            with pytest.raises(ValidationError, match="Audit event validation failed"):
                client.send(_make_mock_event())

            mock_logger.emit.assert_not_called()
        finally:
            patcher.stop()

    def test_send_invalid_tenant_id_raises(self):
        client, mock_logger, _, _, patcher, _ = _make_mocked_client()
        try:
            event = _make_mock_event(tenant_id="bad tenant id")

            with pytest.raises(ValueError):
                client.send(event)

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


class TestAuditClientProtocol:
    @patch("sap_cloud_sdk.core.auditlog_ng.client.GRPCLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_grpc_is_default(
        self, mock_provider_cls, mock_grpc_exporter_cls, monkeypatch
    ):
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_PROTOCOL", raising=False)
        AuditClient(_make_config())
        mock_grpc_exporter_cls.assert_called_once()

    @patch("sap_cloud_sdk.core.auditlog_ng.client.HTTPLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_http_protobuf_protocol(
        self, mock_provider_cls, mock_http_exporter_cls, monkeypatch
    ):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
        AuditClient(
            _make_config(
                cert_file="client.pem", key_file="client.key", ca_file="ca.pem"
            )
        )
        mock_http_exporter_cls.assert_called_once()
        _, kwargs = mock_http_exporter_cls.call_args
        assert kwargs["endpoint"] == "localhost:4317"
        assert kwargs["client_certificate_file"] == "client.pem"
        assert kwargs["client_key_file"] == "client.key"
        assert kwargs["certificate_file"] == "ca.pem"

    @patch("sap_cloud_sdk.core.auditlog_ng.client.HTTPLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_http_compression(
        self, mock_provider_cls, mock_http_exporter_cls, monkeypatch
    ):
        from opentelemetry.exporter.otlp.proto.http import (
            Compression as HTTPCompression,
        )

        monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
        AuditClient(_make_config(compression=True))
        _, kwargs = mock_http_exporter_cls.call_args
        assert kwargs["compression"] == HTTPCompression.Gzip

    @patch("sap_cloud_sdk.core.auditlog_ng.client.GRPCLogExporter")
    @patch("sap_cloud_sdk.core.auditlog_ng.client.LoggerProvider")
    def test_unsupported_protocol_raises(
        self, mock_provider_cls, mock_exporter_cls, monkeypatch
    ):
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/json")
        with pytest.raises(ValueError, match="Unsupported OTEL_EXPORTER_OTLP_PROTOCOL"):
            AuditClient(_make_config())


class TestFillCommonFromAuthContext:
    def setup_method(self):
        set_auth_context(None)

    def teardown_method(self):
        set_auth_context(None)

    def _make_claims(self, app_tid="tid-123", user_uuid="uid-456"):
        claims = MagicMock()
        claims.app_tid = app_tid
        claims.user_uuid = user_uuid
        return claims

    def test_no_context_sets_timestamp_only(self):
        event = pb.DataAccess()
        _fill_common_from_auth_context(event)
        assert event.common.timestamp.seconds > 0
        assert event.common.tenant_id == ""
        assert event.common.user_initiator_id == ""

    def test_with_context_fills_tenant_and_user(self):
        set_auth_context(self._make_claims())
        event = pb.DataAccess()
        _fill_common_from_auth_context(event)
        assert event.common.tenant_id == "tid-123"
        assert event.common.user_initiator_id == "uid-456"
        assert event.common.timestamp.seconds > 0

    def test_does_not_overwrite_explicit_tenant(self):
        set_auth_context(self._make_claims(app_tid="ctx-tid"))
        event = pb.DataAccess()
        event.common.tenant_id = "explicit-tid"
        _fill_common_from_auth_context(event)
        assert event.common.tenant_id == "explicit-tid"

    def test_does_not_overwrite_explicit_user(self):
        set_auth_context(self._make_claims(user_uuid="ctx-uid"))
        event = pb.DataAccess()
        event.common.user_initiator_id = "explicit-uid"
        _fill_common_from_auth_context(event)
        assert event.common.user_initiator_id == "explicit-uid"

    def test_does_not_overwrite_explicit_timestamp(self):
        fixed = datetime(2024, 1, 1, tzinfo=timezone.utc)
        event = pb.DataAccess()
        event.common.timestamp.FromDatetime(fixed)
        _fill_common_from_auth_context(event)
        assert event.common.timestamp.seconds == int(fixed.timestamp())

    def test_event_without_common_field_is_skipped(self):
        event = MagicMock(spec=[])  # no 'common' attribute
        _fill_common_from_auth_context(event)  # must not raise
