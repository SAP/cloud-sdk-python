"""Tests for Starlette/FastAPI middlewares and auto_instrument wiring."""

import asyncio
import pytest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch, create_autospec

from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider

from sap_cloud_sdk.core.telemetry.middlewares.base import HeaderSpanMiddleware
from sap_cloud_sdk.core.telemetry.middlewares.starlette import A2AStarletteMiddleware
from sap_cloud_sdk.core.telemetry.auto_instrument import auto_instrument


class _CustomMiddleware(HeaderSpanMiddleware):
    @property
    def header_name(self) -> str:
        return "x-custom"

    @property
    def span_attribute(self) -> str:
        return "custom.value"


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestA2AStarletteMiddleware:
    def test_header_name(self):
        assert A2AStarletteMiddleware(MagicMock()).header_name == "x-origin"

    def test_span_attribute(self):
        assert A2AStarletteMiddleware(MagicMock()).span_attribute == "a2a.origin"

    def test_register_calls_add_middleware_on_app(self):
        app = MagicMock()
        m = A2AStarletteMiddleware(app)
        m.register()
        app.add_middleware.assert_called_once_with(m.asgi_middleware_class)

    def test_captures_x_origin_header(self):
        m = A2AStarletteMiddleware(MagicMock())
        captured = []

        async def app(scope, receive, send):
            captured.append(m._context_var.get())

        async def run():
            instance = m.asgi_middleware_class(app)
            await instance(
                {"type": "http", "headers": [(b"x-origin", b"agent-a")]},
                None, None,
            )

        _run(run())
        assert captured == ["agent-a"]

    def test_stamps_a2a_origin_on_span(self):
        m = A2AStarletteMiddleware(MagicMock())
        m._context_var.set("agent-b")
        span = MagicMock()
        span.is_recording.return_value = True
        m.span_processor.on_start(span)
        span.set_attribute.assert_called_once_with("a2a.origin", "agent-b")


@pytest.fixture
def mock_traceloop_components():
    with ExitStack() as stack:
        mocks = {
            "traceloop": stack.enter_context(
                patch("sap_cloud_sdk.core.telemetry.auto_instrument.Traceloop")
            ),
            "grpc_exporter": stack.enter_context(
                patch("sap_cloud_sdk.core.telemetry.auto_instrument.GRPCSpanExporter")
            ),
            "transformer": stack.enter_context(
                patch(
                    "sap_cloud_sdk.core.telemetry.auto_instrument.GenAIAttributeTransformer"
                )
            ),
            "baggage_processor": stack.enter_context(
                patch(
                    "sap_cloud_sdk.core.telemetry.auto_instrument.BaggageSpanProcessor"
                )
            ),
            "get_tracer_provider": stack.enter_context(
                patch(
                    "sap_cloud_sdk.core.telemetry.auto_instrument.trace.get_tracer_provider",
                    return_value=create_autospec(SDKTracerProvider),
                )
            ),
            "create_resource": stack.enter_context(
                patch(
                    "sap_cloud_sdk.core.telemetry.auto_instrument.create_resource_attributes_from_env"
                )
            ),
            "get_app_name": stack.enter_context(
                patch("sap_cloud_sdk.core.telemetry.auto_instrument._get_app_name")
            ),
        }
        mocks["get_app_name"].return_value = "test-app"
        mocks["create_resource"].return_value = {}
        yield mocks


class TestAutoInstrumentMiddlewares:
    def test_calls_register_and_adds_span_processor(self, mock_traceloop_components):
        m1 = _CustomMiddleware()
        m1.register = MagicMock()
        app = MagicMock()
        m2 = A2AStarletteMiddleware(app)

        with patch.dict(
            "os.environ",
            {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"},
            clear=True,
        ):
            auto_instrument(middlewares=[m1, m2])

        m1.register.assert_called_once()
        app.add_middleware.assert_called_once_with(m2.asgi_middleware_class)

        provider = mock_traceloop_components["get_tracer_provider"].return_value
        calls = [c.args[0] for c in provider.add_span_processor.call_args_list]
        assert m1.span_processor in calls
        assert m2.span_processor in calls

    def test_no_middleware_leaves_only_baggage_processor(self, mock_traceloop_components):
        with patch.dict(
            "os.environ",
            {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"},
            clear=True,
        ):
            auto_instrument()

        provider = mock_traceloop_components["get_tracer_provider"].return_value
        assert provider.add_span_processor.call_count == 1

    def test_empty_list_leaves_only_baggage_processor(self, mock_traceloop_components):
        with patch.dict(
            "os.environ",
            {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317"},
            clear=True,
        ):
            auto_instrument(middlewares=[])

        provider = mock_traceloop_components["get_tracer_provider"].return_value
        assert provider.add_span_processor.call_count == 1
