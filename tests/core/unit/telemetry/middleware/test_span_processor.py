"""Tests for MiddlewareSpanProcessor."""

import pytest
from unittest.mock import MagicMock

from sap_cloud_sdk.core.telemetry.middleware.span_processor import MiddlewareSpanProcessor


class TestMiddlewareSpanProcessor:
    def _make_recording_span(self):
        span = MagicMock()
        span.is_recording.return_value = True
        return span

    def _make_non_recording_span(self):
        span = MagicMock()
        span.is_recording.return_value = False
        return span

    def test_on_start_stamps_attributes_from_middleware(self):
        middleware = MagicMock()
        middleware.get_attributes.return_value = {"sap.tenancy.tenant_id": "t1", "user.id": "u1"}
        processor = MiddlewareSpanProcessor([middleware])
        span = self._make_recording_span()

        processor.on_start(span, None)

        span.set_attribute.assert_any_call("sap.tenancy.tenant_id", "t1")
        span.set_attribute.assert_any_call("user.id", "u1")

    def test_on_start_stamps_attributes_from_multiple_middlewares(self):
        mw1 = MagicMock()
        mw1.get_attributes.return_value = {"sap.tenancy.tenant_id": "t1"}
        mw2 = MagicMock()
        mw2.get_attributes.return_value = {"user.id": "u1"}
        processor = MiddlewareSpanProcessor([mw1, mw2])
        span = self._make_recording_span()

        processor.on_start(span, None)

        span.set_attribute.assert_any_call("sap.tenancy.tenant_id", "t1")
        span.set_attribute.assert_any_call("user.id", "u1")

    def test_on_start_skips_non_recording_span(self):
        middleware = MagicMock()
        middleware.get_attributes.return_value = {"key": "val"}
        processor = MiddlewareSpanProcessor([middleware])
        span = self._make_non_recording_span()

        processor.on_start(span, None)

        span.set_attribute.assert_not_called()
        middleware.get_attributes.assert_not_called()

    def test_on_start_catches_middleware_exception(self):
        middleware = MagicMock()
        middleware.get_attributes.side_effect = RuntimeError("boom")
        processor = MiddlewareSpanProcessor([middleware])
        span = self._make_recording_span()

        # Must not raise
        processor.on_start(span, None)

        span.set_attribute.assert_not_called()

    def test_on_start_continues_after_one_middleware_exception(self):
        mw1 = MagicMock()
        mw1.get_attributes.side_effect = RuntimeError("boom")
        mw2 = MagicMock()
        mw2.get_attributes.return_value = {"key": "val"}
        processor = MiddlewareSpanProcessor([mw1, mw2])
        span = self._make_recording_span()

        processor.on_start(span, None)

        span.set_attribute.assert_called_once_with("key", "val")

    def test_on_start_with_empty_attributes_does_nothing(self):
        middleware = MagicMock()
        middleware.get_attributes.return_value = {}
        processor = MiddlewareSpanProcessor([middleware])
        span = self._make_recording_span()

        processor.on_start(span, None)

        span.set_attribute.assert_not_called()

    def test_on_end_does_nothing(self):
        processor = MiddlewareSpanProcessor([])
        processor.on_end(MagicMock())  # should not raise

    def test_shutdown_does_nothing(self):
        processor = MiddlewareSpanProcessor([])
        processor.shutdown()  # should not raise

    def test_force_flush_returns_true(self):
        processor = MiddlewareSpanProcessor([])
        assert processor.force_flush() is True
        assert processor.force_flush(timeout_millis=5000) is True
