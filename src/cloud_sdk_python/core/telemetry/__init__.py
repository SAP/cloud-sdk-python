"""OpenTelemetry telemetry for Cloud SDK.

This module provides decorator-based telemetry and direct metric recording
functions for SDK operations, plus automatic HTTP client instrumentation.

"""

from cloud_sdk_python.core.telemetry.telemetry import (
    record_request_metric,
    record_error_metric,
    record_aicore_metric,
    set_tenant_id,
    get_tenant_id,
)
from cloud_sdk_python.core.telemetry.module import Module
from cloud_sdk_python.core.telemetry.operation import Operation
from cloud_sdk_python.core.telemetry.genai_operation import GenAIOperation
from cloud_sdk_python.core.telemetry.metrics_decorator import record_metrics
from cloud_sdk_python.core.telemetry.auto_instrument import auto_instrument
from cloud_sdk_python.core.telemetry.tracer import (
    context_overlay,
    get_current_span,
    add_span_attribute,
    chat_span,
    execute_tool_span,
    invoke_agent_span,
)

__all__ = [
    "Module",
    "Operation",
    "GenAIOperation",
    "record_metrics",
    "record_request_metric",
    "record_error_metric",
    "record_aicore_metric",
    "set_tenant_id",
    "get_tenant_id",
    "auto_instrument",
    "context_overlay",
    "get_current_span",
    "add_span_attribute",
    "chat_span",
    "execute_tool_span",
    "invoke_agent_span",
]
