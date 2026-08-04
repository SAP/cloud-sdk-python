"""Tests for _instrument() internal telemetry initialization."""

from contextlib import ExitStack
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider

from sap_cloud_sdk.core.telemetry._instrument import _instrument

_MOD = "sap_cloud_sdk.core.telemetry._instrument"


@pytest.fixture
def mock_traceloop_components():
    with ExitStack() as stack:
        mocks = {
            "traceloop": stack.enter_context(patch(f"{_MOD}.Traceloop")),
            "grpc_exporter": stack.enter_context(patch(f"{_MOD}.GRPCSpanExporter")),
            "http_exporter": stack.enter_context(patch(f"{_MOD}.HTTPSpanExporter")),
            "console_exporter": stack.enter_context(patch(f"{_MOD}.ConsoleSpanExporter")),
            "transformer": stack.enter_context(patch(f"{_MOD}.GenAIAttributeTransformer")),
            "baggage_processor": stack.enter_context(patch(f"{_MOD}.BaggageSpanProcessor")),
            "propagated_processor": stack.enter_context(patch(f"{_MOD}.PropagatedAttributesSpanProcessor")),
            "runtime_context_processor": stack.enter_context(patch(f"{_MOD}.RuntimeContextSpanProcessor")),
            "get_tracer_provider": stack.enter_context(
                patch(f"{_MOD}.trace.get_tracer_provider", return_value=create_autospec(SDKTracerProvider))
            ),
            "create_resource": stack.enter_context(patch(f"{_MOD}.create_resource_attributes_from_env")),
            "get_app_name": stack.enter_context(patch(f"{_MOD}._get_app_name")),
        }
        yield mocks


class TestInstrument:
    def test_with_endpoint_initializes_traceloop(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {"service.name": "test-app"}

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument()

            mock_traceloop_components["traceloop"].init.assert_called_once()
            kwargs = mock_traceloop_components["traceloop"].init.call_args[1]
            assert kwargs["app_name"] == "test-app"
            assert kwargs["should_enrich_metrics"] is True
            assert kwargs["disable_batch"] is False

    def test_uses_grpc_exporter_by_default(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument()

            mock_traceloop_components["grpc_exporter"].assert_called_once_with()
            mock_traceloop_components["http_exporter"].assert_not_called()

    def test_uses_http_protobuf_when_configured(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}

        with patch.dict(
            "os.environ",
            {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318", "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf"},
            clear=True,
        ):
            _instrument()

            mock_traceloop_components["http_exporter"].assert_called_once_with()
            mock_traceloop_components["grpc_exporter"].assert_not_called()

    def test_uses_console_exporter_when_configured(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}

        with patch.dict("os.environ", {"OTEL_TRACES_EXPORTER": "console"}, clear=True):
            _instrument()

            mock_traceloop_components["console_exporter"].assert_called_once_with()
            mock_traceloop_components["grpc_exporter"].assert_not_called()
            mock_traceloop_components["http_exporter"].assert_not_called()

    def test_console_exporter_case_insensitive(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}

        for value in ["CONSOLE", "Console", "CONSOLE"]:
            mock_traceloop_components["console_exporter"].reset_mock()
            mock_traceloop_components["traceloop"].reset_mock()
            with patch.dict("os.environ", {"OTEL_TRACES_EXPORTER": value}, clear=True):
                _instrument()
                mock_traceloop_components["console_exporter"].assert_called_once_with()

    def test_console_wins_when_both_endpoint_and_console_set(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}

        with patch.dict(
            "os.environ",
            {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317", "OTEL_TRACES_EXPORTER": "console"},
            clear=True,
        ):
            _instrument()

            mock_traceloop_components["console_exporter"].assert_called_once_with()
            mock_traceloop_components["grpc_exporter"].assert_not_called()

    def test_console_exporter_wrapped_with_transformer(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}
        console_instance = MagicMock()
        mock_traceloop_components["console_exporter"].return_value = console_instance

        with patch.dict("os.environ", {"OTEL_TRACES_EXPORTER": "console"}, clear=True):
            _instrument()

            mock_traceloop_components["transformer"].assert_called_once_with(console_instance)

    def test_transformer_passed_as_exporter_to_traceloop(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}
        transformer_instance = MagicMock()
        mock_traceloop_components["transformer"].return_value = transformer_instance

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument()

            kwargs = mock_traceloop_components["traceloop"].init.call_args[1]
            assert kwargs["exporter"] == transformer_instance

    def test_disable_batch_propagated_to_traceloop(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument(disable_batch=True)

            kwargs = mock_traceloop_components["traceloop"].init.call_args[1]
            assert kwargs["disable_batch"] is True

    def test_warns_and_returns_when_no_endpoint_or_console(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch(f"{_MOD}.logger") as mock_logger:
                _instrument()

                mock_logger.warning.assert_called_once()
                assert "OTEL_EXPORTER_OTLP_ENDPOINT not set" in mock_logger.warning.call_args[0][0]

    def test_registers_baggage_processor(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}
        baggage_instance = MagicMock()
        mock_traceloop_components["baggage_processor"].return_value = baggage_instance

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument()

            mock_traceloop_components["baggage_processor"].assert_called_once()
            mock_traceloop_components["get_tracer_provider"].return_value.add_span_processor.assert_any_call(
                baggage_instance
            )

    def test_registers_propagated_attributes_processor(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}
        propagated_instance = MagicMock()
        mock_traceloop_components["propagated_processor"].return_value = propagated_instance

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument()

            mock_traceloop_components["propagated_processor"].assert_called_once()
            mock_traceloop_components["get_tracer_provider"].return_value.add_span_processor.assert_any_call(
                propagated_instance
            )

    def test_registers_runtime_context_processor(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}
        rc_instance = MagicMock()
        mock_traceloop_components["runtime_context_processor"].return_value = rc_instance

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument()

            mock_traceloop_components["runtime_context_processor"].assert_called_once()
            mock_traceloop_components["get_tracer_provider"].return_value.add_span_processor.assert_any_call(
                rc_instance
            )

    def test_all_three_processors_registered(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "test-app"
        mock_traceloop_components["create_resource"].return_value = {}

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument()

        assert mock_traceloop_components["get_tracer_provider"].return_value.add_span_processor.call_count == 3

    def test_merges_resource_when_wrapper_installed(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "cloud-sdk-app"
        sap_attrs = {
            "service.name": "cloud-sdk-app",
            "sap.cloud_sdk.name": "SAP Cloud SDK for Python",
            "sap.cloud_sdk.language": "python",
        }
        mock_traceloop_components["create_resource"].return_value = sap_attrs

        wrapper_provider = SDKTracerProvider(
            resource=Resource.create({
                "telemetry.auto.version": "0.62b1",
                "k8s.deployment.name": "cloud-sdk-app-deployment",
                "service.name": "operator-supplied-name",
            })
        )
        mock_traceloop_components["get_tracer_provider"].return_value = wrapper_provider

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument()

            attrs = wrapper_provider.resource.attributes
            assert attrs["telemetry.auto.version"] == "0.62b1"
            assert attrs["k8s.deployment.name"] == "cloud-sdk-app-deployment"
            assert attrs["sap.cloud_sdk.name"] == "SAP Cloud SDK for Python"
            assert attrs["service.name"] == "cloud-sdk-app"

    def test_skips_merge_when_no_wrapper_marker(self, mock_traceloop_components):
        mock_traceloop_components["get_app_name"].return_value = "cloud-sdk-app"
        mock_traceloop_components["create_resource"].return_value = {"sap.cloud_sdk.name": "SAP Cloud SDK for Python"}

        initial_resource = Resource.create({"service.name": "self-installed"})
        plain_provider = SDKTracerProvider(resource=initial_resource)
        mock_traceloop_components["get_tracer_provider"].return_value = plain_provider

        with patch.dict("os.environ", {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"}, clear=True):
            _instrument()

            assert plain_provider.resource is initial_resource
            assert "sap.cloud_sdk.name" not in plain_provider.resource.attributes
