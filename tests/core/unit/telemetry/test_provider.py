"""Tests for telemetry meter provider."""

from unittest.mock import patch, MagicMock, call
import logging
import pytest

from opentelemetry.sdk.metrics import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import AggregationTemporality

from opentelemetry.sdk.resources import Resource

from sap_cloud_sdk.core.telemetry._provider import (
    get_meter,
    shutdown,
    _setup_meter_provider,
    _create_metric_exporter,
    setup_log_provider,
    _create_log_exporter,
    _merge_sdk_resource_into_log_provider,
    _root_logger_has_otel_handler,
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
                _create_metric_exporter()
                mock_grpc.assert_called_once_with(preferred_temporality=_DELTA_TEMPORALITY)
                mock_http.assert_not_called()

    def test_grpc_explicit(self):
        with patch(_GRPC_EXPORTER) as mock_grpc:
            with patch(_HTTP_EXPORTER) as mock_http:
                with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "grpc"}):
                    _create_metric_exporter()
                mock_grpc.assert_called_once_with(preferred_temporality=_DELTA_TEMPORALITY)
                mock_http.assert_not_called()

    def test_http_protobuf(self):
        with patch(_GRPC_EXPORTER) as mock_grpc:
            with patch(_HTTP_EXPORTER) as mock_http:
                with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf"}):
                    _create_metric_exporter()
                mock_http.assert_called_once_with(preferred_temporality=_DELTA_TEMPORALITY)
                mock_grpc.assert_not_called()

    def test_unsupported_protocol_raises(self):
        import pytest
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "http/json"}):
            with pytest.raises(ValueError, match="Unsupported OTEL_EXPORTER_OTLP_PROTOCOL"):
                _create_metric_exporter()


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

                        mock_create.assert_called_once_with()
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


_LOGGING_HANDLER = "sap_cloud_sdk.core.telemetry._provider.LoggingHandler"
_GRPC_LOG_EXPORTER = "sap_cloud_sdk.core.telemetry._provider.GRPCLogExporter"
_HTTP_LOG_EXPORTER = "sap_cloud_sdk.core.telemetry._provider.HTTPLogExporter"


class TestCreateLogExporter:
    def test_grpc_by_default(self):
        with patch(_GRPC_LOG_EXPORTER) as mock_grpc:
            with patch(_HTTP_LOG_EXPORTER) as mock_http:
                _create_log_exporter()
                mock_grpc.assert_called_once_with()
                mock_http.assert_not_called()

    def test_grpc_explicit(self):
        with patch(_GRPC_LOG_EXPORTER) as mock_grpc:
            with patch(_HTTP_LOG_EXPORTER) as mock_http:
                with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "grpc"}):
                    _create_log_exporter()
                mock_grpc.assert_called_once_with()
                mock_http.assert_not_called()

    def test_http_protobuf(self):
        with patch(_GRPC_LOG_EXPORTER) as mock_grpc:
            with patch(_HTTP_LOG_EXPORTER) as mock_http:
                with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf"}):
                    _create_log_exporter()
                mock_http.assert_called_once_with()
                mock_grpc.assert_not_called()

    def test_unsupported_protocol_raises(self):
        import pytest
        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_PROTOCOL": "http/json"}):
            with pytest.raises(ValueError, match="Unsupported OTEL_EXPORTER_OTLP_PROTOCOL"):
                _create_log_exporter()


class TestSetupLogProvider:
    @pytest.fixture(autouse=True)
    def reset_log_provider(self):
        import sap_cloud_sdk.core.telemetry._provider as provider_module
        provider_module._log_provider = None
        yield
        provider_module._log_provider = None

    def test_disabled_returns_none(self):
        config = InstrumentationConfig(enabled=False)
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=config):
            assert setup_log_provider() is None

    def test_normal_path_sets_our_provider(self):
        """No pre-installed provider — we create ours, set it globally, add handler."""
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=_ENABLED_CONFIG):
            with patch("sap_cloud_sdk.core.telemetry._provider.Resource"):
                with patch("sap_cloud_sdk.core.telemetry._provider._create_log_exporter"):
                    with patch("sap_cloud_sdk.core.telemetry._provider.BatchLogRecordProcessor"):
                        # plain MagicMock fails isinstance(x, LoggerProvider) → normal path
                        with patch("sap_cloud_sdk.core.telemetry._provider.get_logger_provider", return_value=MagicMock()):
                            with patch("sap_cloud_sdk.core.telemetry._provider.set_logger_provider") as mock_set:
                                with patch(_LOGGING_HANDLER):
                                    with patch("logging.getLogger"):
                                        result = setup_log_provider()
                                        assert result is not None
                                        mock_set.assert_called_once_with(result)

    def test_normal_path_uses_sdk_resource(self):
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=_ENABLED_CONFIG):
            with patch("sap_cloud_sdk.core.telemetry._provider.create_resource_attributes_from_env", return_value={"service.name": "svc"}) as mock_attrs:
                with patch("sap_cloud_sdk.core.telemetry._provider.Resource") as mock_resource:
                    with patch("sap_cloud_sdk.core.telemetry._provider._create_log_exporter"):
                        with patch("sap_cloud_sdk.core.telemetry._provider.BatchLogRecordProcessor"):
                            with patch("sap_cloud_sdk.core.telemetry._provider.get_logger_provider", return_value=MagicMock()):
                                with patch("sap_cloud_sdk.core.telemetry._provider.LoggerProvider"):
                                    with patch("sap_cloud_sdk.core.telemetry._provider.set_logger_provider"):
                                        with patch(_LOGGING_HANDLER):
                                            with patch("logging.getLogger"):
                                                setup_log_provider()
                                                mock_attrs.assert_called_once()
                                                mock_resource.create.assert_called_once_with({"service.name": "svc"})

    def test_normal_path_installs_handler_on_root_logger(self):
        mock_handler = MagicMock()
        mock_root = MagicMock()
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=_ENABLED_CONFIG):
            with patch("sap_cloud_sdk.core.telemetry._provider.Resource"):
                with patch("sap_cloud_sdk.core.telemetry._provider._create_log_exporter"):
                    with patch("sap_cloud_sdk.core.telemetry._provider.BatchLogRecordProcessor"):
                        with patch("sap_cloud_sdk.core.telemetry._provider.get_logger_provider", return_value=MagicMock()):
                            with patch("sap_cloud_sdk.core.telemetry._provider.set_logger_provider"):
                                with patch(_LOGGING_HANDLER, return_value=mock_handler):
                                    with patch("logging.getLogger", return_value=mock_root):
                                        setup_log_provider()
                                        mock_root.addHandler.assert_called_once_with(mock_handler)

    def test_exception_returns_none(self):
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=_ENABLED_CONFIG):
            with patch("sap_cloud_sdk.core.telemetry._provider.Resource"):
                with patch("sap_cloud_sdk.core.telemetry._provider.get_logger_provider", return_value=MagicMock()):
                    with patch("sap_cloud_sdk.core.telemetry._provider._create_log_exporter", side_effect=Exception("boom")):
                        assert setup_log_provider() is None

    def test_platform_path_merges_resource_no_extra_handler(self):
        """Platform pre-installed provider with a handler — merge resource, add nothing."""
        from opentelemetry.sdk._logs import LoggerProvider as _LP
        external = MagicMock(spec=_LP)
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=_ENABLED_CONFIG):
            with patch("sap_cloud_sdk.core.telemetry._provider.Resource"):
                with patch("sap_cloud_sdk.core.telemetry._provider._create_log_exporter"):
                    with patch("sap_cloud_sdk.core.telemetry._provider.get_logger_provider", return_value=external):
                        with patch("sap_cloud_sdk.core.telemetry._provider._merge_sdk_resource_into_log_provider") as mock_merge:
                            with patch("sap_cloud_sdk.core.telemetry._provider._root_logger_has_otel_handler", return_value=True):
                                result = setup_log_provider()
                                assert result is external
                                mock_merge.assert_called_once()
                                external.add_log_record_processor.assert_not_called()

    def test_platform_path_adds_handler_when_none_present(self):
        """Platform set provider but no LoggingHandler — we add handler, no extra processor."""
        from opentelemetry.sdk._logs import LoggerProvider as _LP
        external = MagicMock(spec=_LP)
        with patch("sap_cloud_sdk.core.telemetry._provider.get_config", return_value=_ENABLED_CONFIG):
            with patch("sap_cloud_sdk.core.telemetry._provider.Resource"):
                with patch("sap_cloud_sdk.core.telemetry._provider.get_logger_provider", return_value=external):
                    with patch("sap_cloud_sdk.core.telemetry._provider._merge_sdk_resource_into_log_provider"):
                        with patch("sap_cloud_sdk.core.telemetry._provider._root_logger_has_otel_handler", return_value=False):
                            with patch(_LOGGING_HANDLER) as mock_handler_cls:
                                with patch("logging.getLogger"):
                                    setup_log_provider()
                                    external.add_log_record_processor.assert_not_called()
                                    mock_handler_cls.assert_called_once_with(logger_provider=external)


class TestMergeSdkResourceIntoLogProvider:
    def test_updates_provider_resource(self):
        from opentelemetry.sdk._logs import LoggerProvider as _LP
        from opentelemetry.sdk.resources import Resource as _R

        sdk_resource = _R({"sap.cloud_sdk.language": "python"})
        provider = _LP(resource=_R({"service.name": "svc"}))

        _merge_sdk_resource_into_log_provider(provider, sdk_resource)

        assert provider._resource.attributes["sap.cloud_sdk.language"] == "python"
        assert provider._resource.attributes["service.name"] == "svc"

    def test_updates_active_logger_resources(self):
        from opentelemetry.sdk._logs import LoggerProvider as _LP
        from opentelemetry.sdk.resources import Resource as _R

        sdk_resource = _R({"sap.cloud_sdk.language": "python"})
        provider = _LP(resource=_R({"service.name": "svc"}))
        logger_instance = provider.get_logger("test.module")

        _merge_sdk_resource_into_log_provider(provider, sdk_resource)

        # The logger already in the active set gets the updated resource
        assert logger_instance._resource.attributes["sap.cloud_sdk.language"] == "python"  # ty: ignore[unresolved-attribute]

    def test_sdk_attrs_win_on_collision(self):
        from opentelemetry.sdk._logs import LoggerProvider as _LP
        from opentelemetry.sdk.resources import Resource as _R

        sdk_resource = _R({"service.name": "sdk-name"})
        provider = _LP(resource=_R({"service.name": "platform-name"}))

        _merge_sdk_resource_into_log_provider(provider, sdk_resource)

        assert provider._resource.attributes["service.name"] == "sdk-name"


class TestRootLoggerHasOtelHandler:
    def test_returns_false_when_no_handler(self):
        root = logging.getLogger()
        original = root.handlers[:]
        root.handlers = []
        try:
            assert _root_logger_has_otel_handler() is False
        finally:
            root.handlers = original

    def test_returns_true_when_handler_present(self):
        from opentelemetry.instrumentation.logging.handler import LoggingHandler as OtelHandler
        root = logging.getLogger()
        original = root.handlers[:]
        mock_provider = MagicMock()
        handler = OtelHandler(logger_provider=mock_provider)
        root.handlers = [handler]
        try:
            assert _root_logger_has_otel_handler() is True
        finally:
            root.handlers = original

    def test_returns_true_when_sdk_level_handler_present(self):
        from opentelemetry.sdk._logs import LoggingHandler as SDKHandler
        root = logging.getLogger()
        original = root.handlers[:]
        mock_provider = MagicMock()
        handler = SDKHandler(logger_provider=mock_provider)
        root.handlers = [handler]
        try:
            assert _root_logger_has_otel_handler() is True
        finally:
            root.handlers = original
