"""Tests for telemetry meter provider."""

from unittest.mock import patch, MagicMock

from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import AggregationTemporality

from sap_cloud_sdk.core.telemetry._provider import (
    get_meter,
    shutdown,
    _setup_meter_provider,
    _create_metric_exporter,
)
from sap_cloud_sdk.core.telemetry.config import InstrumentationConfig

_DELTA_TEMPORALITY = {
    Counter: AggregationTemporality.DELTA,
    Histogram: AggregationTemporality.DELTA,
    ObservableCounter: AggregationTemporality.DELTA,
    ObservableGauge: AggregationTemporality.DELTA,
    ObservableUpDownCounter: AggregationTemporality.DELTA,
    UpDownCounter: AggregationTemporality.DELTA,
}

_GRPC_EXPORTER = "sap_cloud_sdk.core.telemetry._provider.GRPCMetricExporter"
_HTTP_EXPORTER = "sap_cloud_sdk.core.telemetry._provider.HTTPMetricExporter"
_ENABLED_CONFIG = InstrumentationConfig(
    enabled=True, service_name="test-service", otlp_endpoint="http://localhost:4317"
)
_ENDPOINT = "http://localhost:4317"


class TestGetMeter:
    def test_get_meter_returns_meter(self):
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        provider_module._meter_provider = None
        provider_module._meter = None

        with patch("sap_cloud_sdk.core.telemetry._provider._setup_meter_provider") as mock_setup:
            mock_setup.return_value = MagicMock()
            with patch("opentelemetry.metrics.get_meter", return_value=MagicMock()) as mock_get_meter:
                meter = get_meter()
                assert meter is mock_get_meter.return_value
                mock_setup.assert_called_once()

    def test_get_meter_returns_singleton(self):
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        provider_module._meter_provider = None
        provider_module._meter = None

        with patch("sap_cloud_sdk.core.telemetry._provider._setup_meter_provider", return_value=MagicMock()):
            with patch("opentelemetry.metrics.get_meter", return_value=MagicMock()) as mock_get_meter:
                meter1 = get_meter()
                meter2 = get_meter()
                assert meter1 is meter2

    def test_get_meter_when_provider_setup_fails(self):
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        provider_module._meter_provider = None
        provider_module._meter = None

        with patch("sap_cloud_sdk.core.telemetry._provider._setup_meter_provider", return_value=None):
            with patch("opentelemetry.metrics.get_meter_provider") as mock_get_provider:
                mock_no_op_meter = MagicMock()
                mock_get_provider.return_value.get_meter.return_value = mock_no_op_meter

                meter = get_meter()

                assert meter is mock_no_op_meter

    def test_get_meter_initializes_provider_once(self):
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        provider_module._meter_provider = None
        provider_module._meter = None

        with patch("sap_cloud_sdk.core.telemetry._provider._setup_meter_provider") as mock_setup:
            mock_setup.return_value = MagicMock()
            with patch("opentelemetry.metrics.get_meter", return_value=MagicMock()):
                get_meter()
                get_meter()
                get_meter()
                assert mock_setup.call_count == 1


class TestShutdown:
    def test_shutdown_with_active_provider(self):
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        mock_provider = MagicMock()
        provider_module._meter_provider = mock_provider

        shutdown()

        mock_provider.shutdown.assert_called_once()
        assert provider_module._meter_provider is None

    def test_shutdown_with_no_provider(self):
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        provider_module._meter_provider = None
        shutdown()  # should not raise

    def test_shutdown_handles_exception(self):
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        mock_provider = MagicMock()
        mock_provider.shutdown.side_effect = Exception("Shutdown error")
        provider_module._meter_provider = mock_provider

        shutdown()  # should not raise

        assert provider_module._meter_provider is None


class TestCreateMetricExporter:
    def test_grpc_by_default(self):
        with patch(_GRPC_EXPORTER) as mock_grpc:
            with patch(_HTTP_EXPORTER) as mock_http:
                _create_metric_exporter(_ENDPOINT)
                mock_grpc.assert_called_once_with(endpoint=_ENDPOINT, preferred_temporality=_DELTA_TEMPORALITY)
                mock_http.assert_not_called()

    def test_grpc_explicit(self):
        with patch(_GRPC_EXPORTER) as mock_grpc:
            with patch(_HTTP_EXPORTER) as mock_http:
                with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "grpc"}):
                    _create_metric_exporter(_ENDPOINT)
                mock_grpc.assert_called_once_with(endpoint=_ENDPOINT, preferred_temporality=_DELTA_TEMPORALITY)
                mock_http.assert_not_called()

    def test_http_protobuf(self):
        with patch(_GRPC_EXPORTER) as mock_grpc:
            with patch(_HTTP_EXPORTER) as mock_http:
                with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf"}):
                    _create_metric_exporter(_ENDPOINT)
                mock_http.assert_called_once_with(endpoint=_ENDPOINT, preferred_temporality=_DELTA_TEMPORALITY)
                mock_grpc.assert_not_called()

    def test_unsupported_protocol_raises(self):
        import pytest
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "http/json"}):
            with pytest.raises(ValueError, match="Unsupported OTEL_EXPORTER_OTLP_PROTOCOL"):
                _create_metric_exporter(_ENDPOINT)


class TestSetupMeterProvider:
    def test_setup_disabled(self):
        config = InstrumentationConfig(enabled=False)
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=config):
            assert _setup_meter_provider() is None

    def test_delegates_to_create_metric_exporter(self):
        mock_exporter = MagicMock()
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=_ENABLED_CONFIG):
            with patch("sap_cloud_sdk.core.telemetry._provider.Resource"):
                with patch("sap_cloud_sdk.core.telemetry._provider._create_metric_exporter", return_value=mock_exporter) as mock_create:
                    with patch("sap_cloud_sdk.core.telemetry._provider.PeriodicExportingMetricReader") as mock_reader:
                        with patch("sap_cloud_sdk.core.telemetry._provider.MeterProvider"):
                            with patch("opentelemetry.metrics.set_meter_provider"):
                                _setup_meter_provider()

                        mock_create.assert_called_once_with(_ENABLED_CONFIG.otlp_endpoint)
                        mock_reader.assert_called_once_with(exporter=mock_exporter)

    def test_unsupported_protocol_returns_none(self):
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=_ENABLED_CONFIG):
            with patch("sap_cloud_sdk.core.telemetry._provider.Resource"):
                with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "http/json"}):
                    assert _setup_meter_provider() is None

    def test_returns_configured_provider(self):
        mock_provider = MagicMock()
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=_ENABLED_CONFIG):
            with patch("sap_cloud_sdk.core.telemetry._provider.Resource"):
                with patch("sap_cloud_sdk.core.telemetry._provider._create_metric_exporter"):
                    with patch("sap_cloud_sdk.core.telemetry._provider.PeriodicExportingMetricReader"):
                        with patch("sap_cloud_sdk.core.telemetry._provider.MeterProvider", return_value=mock_provider):
                            with patch("opentelemetry.metrics.set_meter_provider"):
                                assert _setup_meter_provider() is mock_provider
