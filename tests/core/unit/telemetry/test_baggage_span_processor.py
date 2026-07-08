"""Tests for BaggageSpanProcessor."""

from typing import Any, Dict
from unittest.mock import MagicMock

from opentelemetry import baggage, context

from sap_cloud_sdk.core.telemetry.span_processors.baggage_span_processor import (
    ALLOW_ALL_BAGGAGE_KEYS,
    BaggageSpanProcessor,
)


def _make_context_with_baggage(entries: Dict[str, Any]):
    ctx = context.get_current()
    for k, v in entries.items():
        ctx = baggage.set_baggage(k, v, context=ctx)
    return ctx


def _make_recording_span(span_id: int = 1):
    span = MagicMock()
    span.is_recording.return_value = True
    span.context.span_id = span_id
    return span


def _make_ended_span(span_id: int = 1, attributes: Dict[str, Any] | None = None):
    span = MagicMock()
    span.context.span_id = span_id
    span._attributes = dict(attributes or {})
    return span


class TestBaggageSpanProcessorOnStart:
    def setup_method(self):
        self.processor = BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS)

    def test_copies_all_baggage_to_span(self):
        ctx = _make_context_with_baggage({"user.id": "u1", "session.id": "s1"})
        span = _make_recording_span()

        self.processor.on_start(span, ctx)

        span.set_attribute.assert_any_call("user.id", "u1")
        span.set_attribute.assert_any_call("session.id", "s1")

    def test_predicate_filters_keys(self):
        ctx = _make_context_with_baggage({"keep.this": "yes", "drop.this": "no"})
        span = _make_recording_span()
        processor = BaggageSpanProcessor(lambda k: k.startswith("keep"))

        processor.on_start(span, ctx)

        span.set_attribute.assert_called_once_with("keep.this", "yes")

    def test_no_op_when_baggage_empty(self):
        span = _make_recording_span()
        self.processor.on_start(span, context.get_current())
        span.set_attribute.assert_not_called()

    def test_no_op_for_non_recording_span(self):
        ctx = _make_context_with_baggage({"gen_ai.conversation.id": "abc"})
        span = MagicMock()
        span.is_recording.return_value = False

        self.processor.on_start(span, ctx)

        span.set_attribute.assert_not_called()
        assert not self.processor._pending

    def test_snapshots_override_key_when_present_in_baggage(self):
        ctx = _make_context_with_baggage({"gen_ai.conversation.id": "caller-uuid"})
        span = _make_recording_span(span_id=42)

        self.processor.on_start(span, ctx)

        assert self.processor._pending[42] == {"gen_ai.conversation.id": "caller-uuid"}

    def test_does_not_snapshot_when_override_key_absent(self):
        ctx = _make_context_with_baggage({"other.key": "value"})
        span = _make_recording_span(span_id=42)

        self.processor.on_start(span, ctx)

        assert 42 not in self.processor._pending


class TestBaggageSpanProcessorOnEnd:
    def setup_method(self):
        self.processor = BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS)

    def test_override_wins_after_framework_overwrites(self):
        ctx = _make_context_with_baggage({"gen_ai.conversation.id": "caller-uuid"})
        span = _make_recording_span(span_id=7)
        self.processor.on_start(span, ctx)

        # simulate framework callback overwriting the value mid-span
        ended = _make_ended_span(
            span_id=7, attributes={"gen_ai.conversation.id": "langgraph-thread-id"}
        )
        self.processor.on_end(ended)

        assert ended._attributes["gen_ai.conversation.id"] == "caller-uuid"

    def test_pending_entry_cleaned_up_after_on_end(self):
        ctx = _make_context_with_baggage({"gen_ai.conversation.id": "caller-uuid"})
        span = _make_recording_span(span_id=7)
        self.processor.on_start(span, ctx)

        ended = _make_ended_span(span_id=7)
        self.processor.on_end(ended)

        assert 7 not in self.processor._pending

    def test_on_end_no_op_when_key_not_in_baggage(self):
        ctx = _make_context_with_baggage({"other.key": "value"})
        span = _make_recording_span(span_id=5)
        self.processor.on_start(span, ctx)

        ended = _make_ended_span(
            span_id=5, attributes={"gen_ai.conversation.id": "framework-set"}
        )
        self.processor.on_end(ended)

        # no override was snapshotted so framework value is untouched
        assert ended._attributes["gen_ai.conversation.id"] == "framework-set"

    def test_on_end_no_op_for_unknown_span_id(self):
        ended = _make_ended_span(
            span_id=99, attributes={"gen_ai.conversation.id": "framework-set"}
        )
        self.processor.on_end(ended)  # no KeyError
        assert ended._attributes["gen_ai.conversation.id"] == "framework-set"

    def test_on_end_no_op_when_attributes_missing(self):
        ctx = _make_context_with_baggage({"gen_ai.conversation.id": "caller-uuid"})
        span = _make_recording_span(span_id=3)
        self.processor.on_start(span, ctx)

        ended = MagicMock()
        ended.context.span_id = 3
        del ended._attributes  # simulate missing _attributes

        self.processor.on_end(ended)  # must not raise

    def test_on_end_swallows_mutation_error(self):
        ctx = _make_context_with_baggage({"gen_ai.conversation.id": "caller-uuid"})
        span = _make_recording_span(span_id=8)
        self.processor.on_start(span, ctx)

        ended = MagicMock()
        ended.context.span_id = 8
        ended._attributes = MagicMock()
        ended._attributes.update.side_effect = RuntimeError("immutable")

        self.processor.on_end(ended)  # must not raise


class TestBaggageSpanProcessorCustomOverrideKeys:
    def test_custom_override_key_is_enforced(self):
        processor = BaggageSpanProcessor(
            ALLOW_ALL_BAGGAGE_KEYS, override_keys=("my.custom.key",)
        )
        ctx = _make_context_with_baggage({"my.custom.key": "baggage-val"})
        span = _make_recording_span(span_id=1)
        processor.on_start(span, ctx)

        ended = _make_ended_span(
            span_id=1, attributes={"my.custom.key": "framework-val"}
        )
        processor.on_end(ended)

        assert ended._attributes["my.custom.key"] == "baggage-val"

    def test_empty_override_keys_skips_snapshot(self):
        processor = BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS, override_keys=())
        ctx = _make_context_with_baggage({"gen_ai.conversation.id": "caller-uuid"})
        span = _make_recording_span(span_id=1)
        processor.on_start(span, ctx)

        assert not processor._pending
