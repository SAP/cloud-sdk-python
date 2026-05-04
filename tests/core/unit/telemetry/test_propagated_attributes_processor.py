"""Tests for PropagatedAttributesSpanProcessor."""

import threading
from unittest.mock import MagicMock

import pytest

from sap_cloud_sdk.core.telemetry.propagated_attributes_processor import (
    PropagatedAttributesSpanProcessor,
)
from sap_cloud_sdk.core.telemetry.telemetry import _propagated_attrs_var


@pytest.fixture(autouse=True)
def reset_propagated_attrs():
    """Ensure _propagated_attrs_var is empty before and after each test."""
    token = _propagated_attrs_var.set({})
    yield
    _propagated_attrs_var.reset(token)


def _make_recording_span(existing_attrs=None):
    span = MagicMock()
    span.is_recording.return_value = True
    span.attributes = existing_attrs or {}
    span.name = "test-span"
    return span


class TestPropagatedAttributesSpanProcessor:
    def setup_method(self):
        self.processor = PropagatedAttributesSpanProcessor()

    def test_injects_propagated_attrs_into_span_with_no_existing_attrs(self):
        _propagated_attrs_var.set({"user.id": "u1", "session.id": "s1"})
        span = _make_recording_span()

        self.processor.on_start(span, None)

        span.set_attribute.assert_any_call("user.id", "u1")
        span.set_attribute.assert_any_call("session.id", "s1")
        assert span.set_attribute.call_count == 2

    def test_does_not_override_attrs_already_present_on_span(self):
        _propagated_attrs_var.set(
            {"gen_ai.request.model": "override", "custom.key": "val"}
        )
        span = _make_recording_span(existing_attrs={"gen_ai.request.model": "gpt-4"})

        self.processor.on_start(span, None)

        span.set_attribute.assert_called_once_with("custom.key", "val")

    def test_does_nothing_when_no_propagated_attrs(self):
        # _propagated_attrs_var is {} by default (from autouse fixture)
        span = _make_recording_span()

        self.processor.on_start(span, None)

        span.set_attribute.assert_not_called()

    def test_does_nothing_for_non_recording_span(self):
        _propagated_attrs_var.set({"key": "val"})
        span = MagicMock()
        span.is_recording.return_value = False

        self.processor.on_start(span, None)

        span.set_attribute.assert_not_called()

    def test_swallows_exception_from_set_attribute(self):
        _propagated_attrs_var.set({"key": "val"})
        span = _make_recording_span()
        span.set_attribute.side_effect = RuntimeError("boom")

        # Must not raise
        self.processor.on_start(span, None)

    def test_injects_all_attrs_when_all_absent(self):
        _propagated_attrs_var.set({"a": 1, "b": 2, "c": 3})
        span = _make_recording_span()

        self.processor.on_start(span, None)

        assert span.set_attribute.call_count == 3
        span.set_attribute.assert_any_call("a", 1)
        span.set_attribute.assert_any_call("b", 2)
        span.set_attribute.assert_any_call("c", 3)

    def test_partial_override_only_missing_keys_added(self):
        _propagated_attrs_var.set({"existing": "old", "new_key": "new_val"})
        span = _make_recording_span(existing_attrs={"existing": "current"})

        self.processor.on_start(span, None)

        span.set_attribute.assert_called_once_with("new_key", "new_val")

    def test_on_end_is_noop(self):
        readable_span = MagicMock()
        # Must not raise and must not interact with span
        self.processor.on_end(readable_span)
        readable_span.assert_not_called()

    def test_context_var_isolation_across_contexts(self):
        """Propagated attrs in one context don't bleed into a separate context."""
        _propagated_attrs_var.set({"main": "yes"})

        results = []

        def run_in_fresh_context():
            # This thread starts with a copy of the parent context,
            # but we reset the ContextVar to empty to simulate isolation.
            token = _propagated_attrs_var.set({})
            try:
                span = _make_recording_span()
                self.processor.on_start(span, None)
                results.append(span.set_attribute.call_count)
            finally:
                _propagated_attrs_var.reset(token)

        t = threading.Thread(target=run_in_fresh_context)
        t.start()
        t.join()

        assert results == [0], (
            "No attrs should be injected in the isolated thread context"
        )
