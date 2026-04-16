"""Tests for auto-instrumentation functionality."""

import pytest
from unittest.mock import patch, MagicMock, create_autospec
from contextlib import ExitStack

from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider

from sap_cloud_sdk.telemetry.auto_instrument import auto_instrument


@pytest.fixture
def mock_traceloop_components():
    """Fixture that mocks Traceloop SDK components."""
    with ExitStack() as stack:
        mocks = {
            'traceloop': stack.enter_context(patch('sap_cloud_sdk.telemetry.auto_instrument.Traceloop')),
            'grpc_exporter': stack.enter_context(patch('sap_cloud_sdk.telemetry.auto_instrument.GRPCSpanExporter')),
            'http_exporter': stack.enter_context(patch('sap_cloud_sdk.telemetry.auto_instrument.HTTPSpanExporter')),
            'console_exporter': stack.enter_context(patch('sap_cloud_sdk.telemetry.auto_instrument.ConsoleSpanExporter')),
            'transformer': stack.enter_context(patch('sap_cloud_sdk.telemetry.auto_instrument.GenAIAttributeTransformer')),
            'baggage_processor': stack.enter_context(patch('sap_cloud_sdk.telemetry.auto_instrument.BaggageSpanProcessor')),
            'get_tracer_provider': stack.enter_context(patch('sap_cloud_sdk.telemetry.auto_instrument.trace.get_tracer_provider', return_value=create_autospec(SDKTracerProvider))),
            'create_resource': stack.enter_context(patch('sap_cloud_sdk.telemetry.auto_instrument.create_resource_attributes_from_env')),
            'get_app_name': stack.enter_context(patch('sap_cloud_sdk.telemetry.auto_instrument._get_app_name')),
        }
        yield mocks


class TestAutoInstrument:
    """Test suite for auto_instrument function."""

    def test_auto_instrument_with_endpoint_success(self, mock_traceloop_components):
        """Test successful auto-instrumentation with valid endpoint."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {'service.name': 'test-app'}

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()

            # Verify Traceloop was initialized
            mock_traceloop_components['traceloop'].init.assert_called_once()
            call_kwargs = mock_traceloop_components['traceloop'].init.call_args[1]
            assert call_kwargs['app_name'] == 'test-app'
            assert call_kwargs['should_enrich_metrics'] is True
            assert call_kwargs['disable_batch'] is False

    def test_auto_instrument_uses_grpc_exporter_by_default(self, mock_traceloop_components):
        """Test that auto_instrument uses gRPC exporter by default, letting it read endpoint from env."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()

            mock_traceloop_components['grpc_exporter'].assert_called_once_with()
            mock_traceloop_components['http_exporter'].assert_not_called()

    def test_auto_instrument_creates_resource_with_attributes(self, mock_traceloop_components):
        """Test that auto_instrument creates resource with correct attributes."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {
            'service.name': 'test-app',
            'sap.cloud_sdk.language': 'python'
        }

        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317',
            'APPFND_CONHOS_APP_NAME': 'test-app',
            'HOSTNAME': 'test-host',
            'APPFND_CONHOS_REGION': 'us-east-1',
            'APPFND_CONHOS_ENVIRONMENT': 'production',
            'APPFND_CONHOS_SUBACCOUNTID': 'sub-123'
        }, clear=True):
            auto_instrument()

            # Verify resource was created
            mock_traceloop_components['create_resource'].assert_called_once()

    def test_auto_instrument_logs_initialization(self, mock_traceloop_components):
        """Test that auto_instrument logs initialization messages."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            with patch('sap_cloud_sdk.telemetry.auto_instrument.logger') as mock_logger:
                auto_instrument()

                # Verify info logs were called
                assert mock_logger.info.call_count >= 1
                # Check for initialization message
                info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any('initialized successfully' in msg.lower() for msg in info_calls)

    def test_auto_instrument_with_trailing_slash(self, mock_traceloop_components):
        """Test that auto_instrument works with a trailing slash endpoint (exporter reads from env)."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317/'}, clear=True):
            auto_instrument()

            mock_traceloop_components['grpc_exporter'].assert_called_once_with()

    def test_auto_instrument_with_http_protobuf_protocol(self, mock_traceloop_components):
        """Test that auto_instrument uses HTTP exporter when OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4318',
            'OTEL_EXPORTER_OTLP_PROTOCOL': 'http/protobuf'
        }, clear=True):
            auto_instrument()

            mock_traceloop_components['http_exporter'].assert_called_once_with()
            mock_traceloop_components['grpc_exporter'].assert_not_called()

    def test_auto_instrument_passes_transformer_to_traceloop(self, mock_traceloop_components):
        """Test that auto_instrument passes the GenAIAttributeTransformer as exporter to Traceloop."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        mock_transformer_instance = MagicMock()
        mock_traceloop_components['transformer'].return_value = mock_transformer_instance

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()

            # Verify transformer was created with base exporter
            mock_traceloop_components['transformer'].assert_called_once()

            # Verify Traceloop.init was called with the transformer as exporter
            call_kwargs = mock_traceloop_components['traceloop'].init.call_args[1]
            assert call_kwargs['exporter'] == mock_transformer_instance

    def test_auto_instrument_legacy_schema_parameter_ignored(self, mock_traceloop_components):
        """Test that legacy_schema parameter is accepted but doesn't affect behavior."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            # Should not raise an error
            auto_instrument()
            auto_instrument()
            auto_instrument()

            # Verify Traceloop was initialized each time
            assert mock_traceloop_components['traceloop'].init.call_count == 3

    def test_auto_instrument_with_console_exporter(self, mock_traceloop_components):
        """Test that auto_instrument uses ConsoleSpanExporter when OTEL_TRACES_EXPORTER=console."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch.dict('os.environ', {'OTEL_TRACES_EXPORTER': 'console'}, clear=True):
            auto_instrument()

            mock_traceloop_components['console_exporter'].assert_called_once_with()
            mock_traceloop_components['grpc_exporter'].assert_not_called()
            mock_traceloop_components['http_exporter'].assert_not_called()
            mock_traceloop_components['traceloop'].init.assert_called_once()

    def test_auto_instrument_console_exporter_case_insensitive(self, mock_traceloop_components):
        """Test that OTEL_TRACES_EXPORTER=console matching is case insensitive."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        for value in ['CONSOLE', 'Console', 'CONSOLE']:
            mock_traceloop_components['console_exporter'].reset_mock()
            mock_traceloop_components['traceloop'].reset_mock()
            with patch.dict('os.environ', {'OTEL_TRACES_EXPORTER': value}, clear=True):
                auto_instrument()
                mock_traceloop_components['console_exporter'].assert_called_once_with()

    def test_auto_instrument_console_wins_when_both_set(self, mock_traceloop_components):
        """Test that console exporter is used when OTEL_TRACES_EXPORTER=console, even if OTLP endpoint is also set."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317',
            'OTEL_TRACES_EXPORTER': 'console',
        }, clear=True):
            auto_instrument()

            mock_traceloop_components['console_exporter'].assert_called_once_with()
            mock_traceloop_components['grpc_exporter'].assert_not_called()
            mock_traceloop_components['http_exporter'].assert_not_called()

    def test_auto_instrument_console_wraps_with_transformer(self, mock_traceloop_components):
        """Test that ConsoleSpanExporter is wrapped with GenAIAttributeTransformer."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        mock_console_instance = MagicMock()
        mock_traceloop_components['console_exporter'].return_value = mock_console_instance

        with patch.dict('os.environ', {'OTEL_TRACES_EXPORTER': 'console'}, clear=True):
            auto_instrument()

            mock_traceloop_components['transformer'].assert_called_once_with(mock_console_instance)

    def test_auto_instrument_without_endpoint_or_console(self):
        """Test that auto_instrument warns when neither OTLP endpoint nor console exporter is configured."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('sap_cloud_sdk.telemetry.auto_instrument.logger') as mock_logger:
                auto_instrument()

                mock_logger.warning.assert_called_once()
                warning_message = mock_logger.warning.call_args[0][0]
                assert "OTEL_EXPORTER_OTLP_ENDPOINT not set" in warning_message

    def test_auto_instrument_disable_batch_can_be_set_to_true(self, mock_traceloop_components):
        """Test that disable_batch=True can be explicitly passed to use SimpleSpanProcessor."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument(disable_batch=True)

            call_kwargs = mock_traceloop_components['traceloop'].init.call_args[1]
            assert call_kwargs['disable_batch'] is True

    def test_auto_instrument_passes_baggage_span_processor(self, mock_traceloop_components):
        """Test that auto_instrument registers a BaggageSpanProcessor on the tracer provider."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        mock_processor_instance = MagicMock()
        mock_traceloop_components['baggage_processor'].return_value = mock_processor_instance

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()

            mock_traceloop_components['baggage_processor'].assert_called_once()
            mock_traceloop_components['get_tracer_provider'].return_value.add_span_processor.assert_called_once_with(mock_processor_instance)
