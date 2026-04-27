"""Tests for HeaderSpanMiddleware base class."""

import asyncio
import pytest
from unittest.mock import MagicMock

from sap_cloud_sdk.core.telemetry.middlewares.base import HeaderSpanMiddleware


class _CustomMiddleware(HeaderSpanMiddleware):
    @property
    def header_name(self) -> str:
        return "x-custom"

    @property
    def span_attribute(self) -> str:
        return "custom.value"


class _UpperMiddleware(HeaderSpanMiddleware):
    @property
    def header_name(self) -> str:
        return "x-env"

    @property
    def span_attribute(self) -> str:
        return "env.name"

    def transform_value(self, value: str) -> str:
        return value.upper()


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


async def _noop_app(scope, receive, send):
    pass


class TestHeaderSpanMiddlewareSubclassing:
    def test_provides_asgi_middleware_class(self):
        m = _CustomMiddleware()
        assert m.asgi_middleware_class is not None
        assert callable(m.asgi_middleware_class)

    def test_provides_span_processor(self):
        m = _CustomMiddleware()
        assert m.span_processor is not None

    def test_each_instance_has_independent_context_var(self):
        a = _CustomMiddleware()
        b = _CustomMiddleware()
        assert a._context_var is not b._context_var

    def test_abstract_class_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            HeaderSpanMiddleware()


class TestSpanProcessor:
    def _make_span(self, recording=True):
        span = MagicMock()
        span.is_recording.return_value = recording
        return span

    def test_stamps_attribute_when_context_var_is_set(self):
        m = _CustomMiddleware()
        m._context_var.set("hello")
        span = self._make_span()
        m.span_processor.on_start(span)
        span.set_attribute.assert_called_once_with("custom.value", "hello")

    def test_no_attribute_when_context_var_is_none(self):
        m = _CustomMiddleware()
        span = self._make_span()
        m.span_processor.on_start(span)
        span.set_attribute.assert_not_called()

    def test_no_attribute_when_span_not_recording(self):
        m = _CustomMiddleware()
        m._context_var.set("hello")
        span = self._make_span(recording=False)
        m.span_processor.on_start(span)
        span.set_attribute.assert_not_called()

    def test_transform_value_is_applied(self):
        m = _UpperMiddleware()
        m._context_var.set("production")
        span = self._make_span()
        m.span_processor.on_start(span)
        span.set_attribute.assert_called_once_with("env.name", "PRODUCTION")

    def test_on_end_is_noop(self):
        m = _CustomMiddleware()
        m.span_processor.on_end(MagicMock())

    def test_force_flush_returns_true(self):
        m = _CustomMiddleware()
        assert m.span_processor.force_flush() is True

    def test_shutdown_is_noop(self):
        m = _CustomMiddleware()
        m.span_processor.shutdown()


class TestASGIMiddleware:
    def test_sets_context_var_for_http_scope(self):
        m = _CustomMiddleware()

        async def run():
            instance = m.asgi_middleware_class(_noop_app)
            await instance(
                {"type": "http", "headers": [(b"x-custom", b"world")]}, None, None
            )

        _run(run())
        assert m._context_var.get() is None

    def test_context_var_holds_value_during_request(self):
        m = _CustomMiddleware()
        captured = []

        async def app(scope, receive, send):
            captured.append(m._context_var.get())

        async def run():
            instance = m.asgi_middleware_class(app)
            await instance(
                {"type": "http", "headers": [(b"x-custom", b"during-request")]},
                None, None,
            )

        _run(run())
        assert captured == ["during-request"]

    def test_context_var_is_none_when_header_absent(self):
        m = _CustomMiddleware()
        captured = []

        async def app(scope, receive, send):
            captured.append(m._context_var.get())

        async def run():
            instance = m.asgi_middleware_class(app)
            await instance({"type": "http", "headers": []}, None, None)

        _run(run())
        assert captured == [None]

    def test_non_http_scope_passes_through(self):
        m = _CustomMiddleware()
        called = []

        async def app(scope, receive, send):
            called.append(scope["type"])

        async def run():
            instance = m.asgi_middleware_class(app)
            await instance(
                {"type": "websocket", "headers": [(b"x-custom", b"ignored")]},
                None, None,
            )

        _run(run())
        assert called == ["websocket"]
        assert m._context_var.get() is None

    def test_context_var_reset_after_request(self):
        m = _CustomMiddleware()

        async def run():
            instance = m.asgi_middleware_class(_noop_app)
            await instance(
                {"type": "http", "headers": [(b"x-custom", b"ephemeral")]},
                None, None,
            )

        _run(run())
        assert m._context_var.get() is None
