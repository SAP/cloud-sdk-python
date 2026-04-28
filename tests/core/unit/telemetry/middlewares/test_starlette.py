"""Tests for Starlette/FastAPI middlewares and auto_instrument wiring."""

import asyncio
import pytest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch, create_autospec

from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
from opentelemetry.sdk.trace.export import SpanProcessor

from sap_cloud_sdk.core.telemetry.middlewares.base import TelemetryMiddleware
from sap_cloud_sdk.core.telemetry.middlewares.starlette import (
    A2AStarletteMiddleware,
    _ASGIHeaderMiddleware,
)
from sap_cloud_sdk.core.telemetry.auto_instrument import auto_instrument


class _CustomMiddleware(TelemetryMiddleware):
    """Minimal concrete middleware for testing auto_instrument wiring."""

    def __init__(self):
        self._span_processor = MagicMock(spec=SpanProcessor)

    @property
    def span_processor(self) -> SpanProcessor:
        return self._span_processor

    def register(self) -> None:
        pass


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestA2AStarletteMiddleware:
    def test_register_calls_add_middleware_on_app(self):
        app = MagicMock()
        m = A2AStarletteMiddleware(app)
        m.register()
        app.add_middleware.assert_called_once()
        assert callable(app.add_middleware.call_args.args[0])

    def test_captures_x_origin_header_into_context_var(self):
        m = A2AStarletteMiddleware(MagicMock())
        captured = []

        async def app(scope, receive, send):
            captured.append(m._context_var.get())

        async def run():
            instance = _ASGIHeaderMiddleware(app, m._context_var, m._extract)
            await instance(
                {"type": "http", "headers": [(b"x-origin", b"agent-a")]},
                None, None,
            )

        _run(run())
        assert captured == [{"a2a.origin": "agent-a"}]

    def test_context_var_is_none_when_header_absent(self):
        m = A2AStarletteMiddleware(MagicMock())
        captured = []

        async def app(scope, receive, send):
            captured.append(m._context_var.get())

        async def run():
            instance = _ASGIHeaderMiddleware(app, m._context_var, m._extract)
            await instance({"type": "http", "headers": []}, None, None)

        _run(run())
        assert captured == [None]

    def test_context_var_reset_after_request(self):
        m = A2AStarletteMiddleware(MagicMock())

        async def run():
            async def noop(scope, receive, send):
                pass
            instance = _ASGIHeaderMiddleware(noop, m._context_var, m._extract)
            await instance(
                {"type": "http", "headers": [(b"x-origin", b"agent-a")]},
                None, None,
            )

        _run(run())
        assert m._context_var.get() is None

    def test_non_http_scope_passes_through(self):
        m = A2AStarletteMiddleware(MagicMock())
        called = []

        async def app(scope, receive, send):
            called.append(scope["type"])

        async def run():
            instance = _ASGIHeaderMiddleware(app, m._context_var, m._extract)
            await instance({"type": "websocket", "headers": []}, None, None)

        _run(run())
        assert called == ["websocket"]

    def test_stamps_attributes_on_span(self):
        m = A2AStarletteMiddleware(MagicMock())
        m._context_var.set({"a2a.origin": "agent-b"})
        span = MagicMock()
        span.is_recording.return_value = True
        m.span_processor.on_start(span)
        span.set_attribute.assert_called_once_with("a2a.origin", "agent-b")

    def test_no_attributes_when_context_var_is_none(self):
        m = A2AStarletteMiddleware(MagicMock())
        span = MagicMock()
        span.is_recording.return_value = True
        m.span_processor.on_start(span)
        span.set_attribute.assert_not_called()

    def test_no_attributes_when_span_not_recording(self):
        m = A2AStarletteMiddleware(MagicMock())
        m._context_var.set({"a2a.origin": "agent-b"})
        span = MagicMock()
        span.is_recording.return_value = False
        m.span_processor.on_start(span)
        span.set_attribute.assert_not_called()


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
        app.add_middleware.assert_called_once()

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
