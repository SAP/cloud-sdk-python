"""Tests for auto-instrumentation functionality."""

import pytest
from unittest.mock import patch, MagicMock, create_autospec
from contextlib import ExitStack

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider

from sap_cloud_sdk.core.telemetry.auto_instrument import auto_instrument


@pytest.fixture
def mock_traceloop_components():
    """Fixture that mocks Traceloop SDK components."""
    with ExitStack() as stack:
        mocks = {
            'traceloop': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument.Traceloop')),
            'grpc_exporter': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument.GRPCSpanExporter')),
            'http_exporter': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument.HTTPSpanExporter')),
            'console_exporter': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument.ConsoleSpanExporter')),
            'transformer': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument.GenAIAttributeTransformer')),
            'baggage_processor': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument.BaggageSpanProcessor')),
            'propagated_processor': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument.PropagatedAttributesSpanProcessor')),
            'get_tracer_provider': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument.trace.get_tracer_provider', return_value=create_autospec(SDKTracerProvider))),
            'create_resource': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument.create_resource_attributes_from_env')),
            'get_app_name': stack.enter_context(patch('sap_cloud_sdk.core.telemetry.auto_instrument._get_app_name')),
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
            with patch('sap_cloud_sdk.core.telemetry.auto_instrument.logger') as mock_logger:
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
            with patch('sap_cloud_sdk.core.telemetry.auto_instrument.logger') as mock_logger:
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
            mock_traceloop_components['get_tracer_provider'].return_value.add_span_processor.assert_any_call(mock_processor_instance)

    def test_auto_instrument_registers_propagated_attributes_processor(self, mock_traceloop_components):
        """Test that auto_instrument registers a PropagatedAttributesSpanProcessor on the tracer provider."""
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        mock_processor_instance = MagicMock()
        mock_traceloop_components['propagated_processor'].return_value = mock_processor_instance

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()

            mock_traceloop_components['propagated_processor'].assert_called_once()
            mock_traceloop_components['get_tracer_provider'].return_value.add_span_processor.assert_any_call(mock_processor_instance)

    def test_auto_instrument_merges_resource_when_wrapper_installed(self, mock_traceloop_components):
        """When an OTel auto-instrumentation wrapper (e.g. an OpenTelemetry-Operator
        init-container injection) has pre-installed a TracerProvider whose Resource
        carries the standard `telemetry.auto.version` marker, auto_instrument merges
        sap-cloud-sdk attrs onto that provider's existing Resource — preserving the
        operator-supplied attrs and adding our SAP enrichment on top."""
        mock_traceloop_components['get_app_name'].return_value = 'cloud-sdk-app'
        sap_attrs = {
            'service.name': 'cloud-sdk-app',
            'sap.cloud_sdk.name': 'SAP Cloud SDK for Python',
            'sap.cloud_sdk.language': 'python',
            'sap.solution_area': 'fina',
            'mlflow.experiment_id': '1635264705567712',
        }
        mock_traceloop_components['create_resource'].return_value = sap_attrs

        wrapper_provider = SDKTracerProvider(
            resource=Resource.create({
                'telemetry.auto.version': '0.62b1',
                'k8s.deployment.name': 'cloud-sdk-app-deployment',
                'service.name': 'cloud-sdk-app-deployment',
            })
        )
        mock_traceloop_components['get_tracer_provider'].return_value = wrapper_provider

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()

            merged_attrs = wrapper_provider.resource.attributes
            # Operator-supplied attrs are preserved.
            assert merged_attrs['telemetry.auto.version'] == '0.62b1'
            assert merged_attrs['k8s.deployment.name'] == 'cloud-sdk-app-deployment'
            # sap-cloud-sdk attrs are added.
            assert merged_attrs['sap.cloud_sdk.name'] == 'SAP Cloud SDK for Python'
            assert merged_attrs['sap.cloud_sdk.language'] == 'python'
            assert merged_attrs['sap.solution_area'] == 'fina'
            assert merged_attrs['mlflow.experiment_id'] == '1635264705567712'

    def test_auto_instrument_skips_merge_when_no_wrapper_marker(self, mock_traceloop_components):
        """When the active TracerProvider's Resource lacks the
        `telemetry.auto.version` marker (e.g. a self-installed provider, or no
        wrapper at all), auto_instrument does not mutate the provider's Resource."""
        mock_traceloop_components['get_app_name'].return_value = 'cloud-sdk-app'
        mock_traceloop_components['create_resource'].return_value = {
            'sap.cloud_sdk.name': 'SAP Cloud SDK for Python',
            'sap.solution_area': 'fina',
        }

        initial_resource = Resource.create({'service.name': 'self-installed'})
        plain_provider = SDKTracerProvider(resource=initial_resource)
        mock_traceloop_components['get_tracer_provider'].return_value = plain_provider

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()

            # Resource is the original instance — no merge took place.
            assert plain_provider.resource is initial_resource
            assert 'sap.cloud_sdk.name' not in plain_provider.resource.attributes
            assert 'sap.solution_area' not in plain_provider.resource.attributes

    def test_auto_instrument_merge_overrides_colliding_service_name(self, mock_traceloop_components):
        """On a wrapper-installed provider, sap-cloud-sdk attrs override colliding
        keys: service.name from APPFND_CONHOS_APP_NAME wins over the operator's
        k8s-deployment-derived service.name."""
        mock_traceloop_components['get_app_name'].return_value = 'cloud-sdk-app'
        mock_traceloop_components['create_resource'].return_value = {
            'service.name': 'cloud-sdk-app',
        }

        wrapper_provider = SDKTracerProvider(
            resource=Resource.create({
                'telemetry.auto.version': '0.62b1',
                'service.name': 'operator-supplied-name',
            })
        )
        mock_traceloop_components['get_tracer_provider'].return_value = wrapper_provider

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument()

            assert wrapper_provider.resource.attributes['service.name'] == 'cloud-sdk-app'


class TestAutoInstrumentMiddlewares:
    """Tests for the middlewares parameter of auto_instrument."""

    def test_middlewares_register_called_and_processor_added(self, mock_traceloop_components):
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        middleware = MagicMock()

        with patch('sap_cloud_sdk.core.telemetry.auto_instrument._register_middleware_processors') as mock_reg:
            with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
                auto_instrument(middlewares=[middleware])
                mock_reg.assert_called_once_with([middleware])

    def test_middlewares_none_does_not_register_processor(self, mock_traceloop_components):
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch('sap_cloud_sdk.core.telemetry.auto_instrument._register_middleware_processors') as mock_reg:
            with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
                auto_instrument(middlewares=None)
                mock_reg.assert_not_called()

    def test_empty_middlewares_list_does_not_register_processor(self, mock_traceloop_components):
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}

        with patch('sap_cloud_sdk.core.telemetry.auto_instrument._register_middleware_processors') as mock_reg:
            with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
                auto_instrument(middlewares=[])
                mock_reg.assert_not_called()

    def test_register_middleware_processors_calls_register_and_adds_processor(self, mock_traceloop_components):
        from sap_cloud_sdk.core.telemetry.auto_instrument import _register_middleware_processors
        from sap_cloud_sdk.core.telemetry.middleware.span_processor import MiddlewareSpanProcessor
        from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
        from unittest.mock import create_autospec

        provider = create_autospec(SDKTracerProvider)
        middleware = MagicMock()

        with patch('sap_cloud_sdk.core.telemetry.auto_instrument.trace.get_tracer_provider', return_value=provider):
            _register_middleware_processors([middleware])

        middleware.register.assert_called_once_with()
        provider.add_span_processor.assert_called_once()
        call_arg = provider.add_span_processor.call_args[0][0]
        assert isinstance(call_arg, MiddlewareSpanProcessor)

    def test_register_middleware_processors_skips_when_unknown_provider(self, mock_traceloop_components):
        from sap_cloud_sdk.core.telemetry.auto_instrument import _register_middleware_processors

        middleware = MagicMock()
        unknown_provider = MagicMock()  # not a TracerProvider instance

        with patch('sap_cloud_sdk.core.telemetry.auto_instrument.trace.get_tracer_provider', return_value=unknown_provider):
            with patch('sap_cloud_sdk.core.telemetry.auto_instrument.logger') as mock_logger:
                _register_middleware_processors([middleware])

                mock_logger.warning.assert_called_once()
                middleware.register.assert_not_called()
                unknown_provider.add_span_processor.assert_not_called()

    def test_baggage_and_middleware_processors_both_added(self, mock_traceloop_components):
        mock_traceloop_components['get_app_name'].return_value = 'test-app'
        mock_traceloop_components['create_resource'].return_value = {}
        middleware = MagicMock()
        mock_baggage_instance = MagicMock()
        mock_traceloop_components['baggage_processor'].return_value = mock_baggage_instance

        with patch.dict('os.environ', {'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'}, clear=True):
            auto_instrument(middlewares=[middleware])

        # add_span_processor called twice: once for baggage, once for middleware
        assert mock_traceloop_components['get_tracer_provider'].return_value.add_span_processor.call_count == 2

