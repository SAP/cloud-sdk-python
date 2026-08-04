"""Tests for RuntimeContextSpanProcessor."""

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider

from sap_cloud_sdk.core.runtime_context._context import RuntimeContext
from sap_cloud_sdk.core.runtime_context.providers._ias import GLOBAL_TENANT_ID, USER_ID
from sap_cloud_sdk.core.runtime_context._keys import TRIGGER_TYPE
from sap_cloud_sdk.core.telemetry.constants import (
    ATTR_SAP_TENANT_ID,
    ATTR_SAP_TRIGGER_TYPE,
    ATTR_USER_ID,
)
from sap_cloud_sdk.core.telemetry.span_processors.runtime_context_span_processor import (
    RuntimeContextSpanProcessor,
)

_PATCH_GET_CONTEXT = "sap_cloud_sdk.core.telemetry.span_processors.runtime_context_span_processor.get_context"


def _recording_span(existing_attrs=None):
    span = MagicMock()
    span.is_recording.return_value = True
    span.attributes = existing_attrs or {}
    return span


def _context_with(**kwargs):
    values = {}
    mapping = {
        "tenant_id": GLOBAL_TENANT_ID,
        "user_id": USER_ID,
        "trigger_type": TRIGGER_TYPE,
    }
    for name, value in kwargs.items():
        values[mapping[name]] = value
    return RuntimeContext(values)


class TestRuntimeContextSpanProcessor:
    def test_stamps_all_three_attrs_when_context_full(self):
        processor = RuntimeContextSpanProcessor()
        span = _recording_span()
        ctx = _context_with(tenant_id="tenant-1", user_id="user-1", trigger_type="ui5")

        with patch(_PATCH_GET_CONTEXT, return_value=ctx):
            processor.on_start(span, None)

        span.set_attribute.assert_any_call(ATTR_SAP_TENANT_ID, "tenant-1")
        span.set_attribute.assert_any_call(ATTR_USER_ID, "user-1")
        span.set_attribute.assert_any_call(ATTR_SAP_TRIGGER_TYPE, "ui5")

    def test_only_stamps_present_keys(self):
        processor = RuntimeContextSpanProcessor()
        span = _recording_span()
        ctx = _context_with(tenant_id="tenant-1")

        with patch(_PATCH_GET_CONTEXT, return_value=ctx):
            processor.on_start(span, None)

        calls = {call.args[0] for call in span.set_attribute.call_args_list}
        assert ATTR_SAP_TENANT_ID in calls
        assert ATTR_USER_ID not in calls
        assert ATTR_SAP_TRIGGER_TYPE not in calls

    def test_does_not_overwrite_existing_span_attrs(self):
        processor = RuntimeContextSpanProcessor()
        span = _recording_span(existing_attrs={ATTR_SAP_TENANT_ID: "already-set"})
        ctx = _context_with(tenant_id="new-tenant")

        with patch(_PATCH_GET_CONTEXT, return_value=ctx):
            processor.on_start(span, None)

        for call in span.set_attribute.call_args_list:
            assert call.args[0] != ATTR_SAP_TENANT_ID

    def test_noop_on_empty_context(self):
        processor = RuntimeContextSpanProcessor()
        span = _recording_span()
        ctx = RuntimeContext()

        with patch(_PATCH_GET_CONTEXT, return_value=ctx):
            processor.on_start(span, None)

        span.set_attribute.assert_not_called()

    def test_noop_when_span_not_recording(self):
        processor = RuntimeContextSpanProcessor()
        span = MagicMock()
        span.is_recording.return_value = False
        ctx = _context_with(tenant_id="tenant-1")

        with patch(_PATCH_GET_CONTEXT, return_value=ctx):
            processor.on_start(span, None)

        span.set_attribute.assert_not_called()

    def test_swallows_exceptions_without_raising(self):
        processor = RuntimeContextSpanProcessor()
        span = _recording_span()
        span.set_attribute.side_effect = RuntimeError("boom")
        ctx = _context_with(tenant_id="tenant-1")

        with patch(_PATCH_GET_CONTEXT, return_value=ctx):
            processor.on_start(span, None)  # must not raise

    def test_on_end_noop(self):
        processor = RuntimeContextSpanProcessor()
        processor.on_end(MagicMock())  # must not raise

    def test_shutdown_noop(self):
        processor = RuntimeContextSpanProcessor()
        processor.shutdown()  # must not raise

    def test_force_flush_returns_true(self):
        processor = RuntimeContextSpanProcessor()
        assert processor.force_flush() is True
