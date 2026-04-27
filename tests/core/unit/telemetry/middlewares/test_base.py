"""Tests for TelemetryMiddleware base interface."""

import pytest
from unittest.mock import MagicMock

from opentelemetry.sdk.trace.export import SpanProcessor

from sap_cloud_sdk.core.telemetry.middlewares.base import TelemetryMiddleware


class _ConcreteMiddleware(TelemetryMiddleware):
    def __init__(self):
        self._span_processor = MagicMock(spec=SpanProcessor)

    @property
    def span_processor(self) -> SpanProcessor:
        return self._span_processor

    def register(self) -> None:
        pass


class TestTelemetryMiddlewareInterface:
    def test_abstract_class_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            TelemetryMiddleware()

    def test_concrete_subclass_can_be_instantiated(self):
        assert _ConcreteMiddleware() is not None

    def test_span_processor_accessible(self):
        assert _ConcreteMiddleware().span_processor is not None

    def test_subclass_missing_register_cannot_be_instantiated(self):
        class _Incomplete(TelemetryMiddleware):
            @property
            def span_processor(self) -> SpanProcessor:
                return MagicMock(spec=SpanProcessor)

        with pytest.raises(TypeError):
            _Incomplete()

    def test_subclass_missing_span_processor_cannot_be_instantiated(self):
        class _Incomplete(TelemetryMiddleware):
            def register(self) -> None:
                pass

        with pytest.raises(TypeError):
            _Incomplete()
