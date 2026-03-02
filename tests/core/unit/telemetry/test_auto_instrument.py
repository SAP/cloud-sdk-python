"""Tests for auto-instrumentation functionality."""

import pytest
from unittest.mock import patch, MagicMock
from contextlib import ExitStack

from cloud_sdk_python.core.telemetry.auto_instrument import auto_instrument


@pytest.fixture
def mock_traceloop_components():
    """Fixture that mocks Traceloop SDK components."""
    with ExitStack() as stack:
        mocks = {
            'traceloop': stack.enter_context(patch('cloud_sdk_python.core.telemetry.auto_instrument.Traceloop')),
            'exporter': stack.enter_context(patch('cloud_sdk_python.core.telemetry.auto_instrument.OTLPSpanExporter')),
            'transformer': stack.enter_context(patch('cloud_sdk_python.core.telemetry.auto_instrument.GenAIAttributeTransformer')),
            'create_resource': stack.enter_context(patch('cloud_sdk_python.core.telemetry.auto_instrument.create_resource_attributes_from_env')),
            'get_conhos_app_name': stack.enter_context(patch('cloud_sdk_python.core.telemetry.auto_instrument._get_conhos_app_name')),
        }
        yield mocks


class TestAutoInstrument:
    """Test suite for auto_instrument function."""

    def test_auto_instrument_without_endpoint(self):
        """Test that auto_instrument warns when OTEL_EXPORTER_OTLP_ENDPOINT is not set."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('cloud_sdk_python.core.telemetry.auto_instrument.logger') as mock_logger:
                auto_instrument()
                
                # Should log warning about missing endpoint
                mock_logger.warning.assert_called_once()
                warning_message = mock_logger.warning.call_args[0][0]
                assert "OTEL_EXPORTER_OTLP_ENDPOINT not set" in warning_message

    def test_auto_instrument_with_endpoint_success(self, mock_traceloop_components):
        """Test successful auto-instrumentation with valid endpoint."""
        mock_traceloop_components['get_conhos_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {'service.name': 'test-app'}
        
        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()
            
            # Verify Traceloop was initialized
            mock_traceloop_components['traceloop'].init.assert_called_once()
            call_kwargs = mock_traceloop_components['traceloop'].init.call_args[1]
            assert call_kwargs['app_name'] == 'test-app'
            assert call_kwargs['should_enrich_metrics'] is True
            assert call_kwargs['disable_batch'] is True

    def test_auto_instrument_appends_v1_traces_to_endpoint(self, mock_traceloop_components):
        """Test that auto_instrument appends /v1/traces to endpoint if not present."""
        mock_traceloop_components['get_conhos_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        
        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()
            
            # Verify exporter was called with /v1/traces appended
            mock_traceloop_components['exporter'].assert_called_once_with(
                endpoint='http://localhost:4317/v1/traces'
            )

    def test_auto_instrument_preserves_existing_v1_traces(self, mock_traceloop_components):
        """Test that auto_instrument doesn't duplicate /v1/traces if already present."""
        mock_traceloop_components['get_conhos_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        
        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317/v1/traces'}, clear=True):
            auto_instrument()
            
            # Verify exporter was called with original endpoint
            mock_traceloop_components['exporter'].assert_called_once_with(
                endpoint='http://localhost:4317/v1/traces'
            )

    def test_auto_instrument_creates_resource_with_attributes(self, mock_traceloop_components):
        """Test that auto_instrument creates resource with correct attributes."""
        mock_traceloop_components['get_conhos_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {
            'service.name': 'test-app',
            'sap.telemetry.sdk.language': 'python'
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
        mock_traceloop_components['get_conhos_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        
        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            with patch('cloud_sdk_python.core.telemetry.auto_instrument.logger') as mock_logger:
                auto_instrument()
                
                # Verify info logs were called
                assert mock_logger.info.call_count >= 1
                # Check for initialization message
                info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any('initialized successfully' in msg.lower() for msg in info_calls)

    def test_auto_instrument_with_trailing_slash(self, mock_traceloop_components):
        """Test that auto_instrument handles endpoint with trailing slash."""
        mock_traceloop_components['get_conhos_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        
        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317/'}, clear=True):
            auto_instrument()
            
            # Verify trailing slash is removed before appending /v1/traces
            mock_traceloop_components['exporter'].assert_called_once_with(
                endpoint='http://localhost:4317/v1/traces'
            )

    def test_auto_instrument_passes_transformer_to_traceloop(self, mock_traceloop_components):
        """Test that auto_instrument passes the GenAIAttributeTransformer as exporter to Traceloop."""
        mock_traceloop_components['get_conhos_app_name'].return_value = 'test-app'
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
        mock_traceloop_components['get_conhos_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        
        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            # Should not raise an error
            auto_instrument()
            auto_instrument()
            auto_instrument()
            
            # Verify Traceloop was initialized each time
            assert mock_traceloop_components['traceloop'].init.call_count == 3
