"""OpenTelemetry telemetry for Cloud SDK.

This module provides decorator-based telemetry and direct metric recording
functions for SDK operations, plus automatic HTTP client instrumentation.

"""

from sap_cloud_sdk.core.telemetry.telemetry import (
    record_request_metric,
    record_error_metric,
    set_tenant_id,
    get_tenant_id,
)
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation
from sap_cloud_sdk.core.telemetry.genai_operation import GenAIOperation
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.auto_instrument import auto_instrument
from sap_cloud_sdk.core.telemetry.tracer import (
    context_overlay,
    get_current_span,
    add_span_attribute,
    chat_span,
    execute_tool_span,
    invoke_agent_span,
)
from sap_cloud_sdk.core.telemetry.middleware import TelemetryMiddleware

__all__ = [
    "Module",
    "Operation",
    "GenAIOperation",
    "record_metrics",
    "record_request_metric",
    "record_error_metric",
    "set_tenant_id",
    "get_tenant_id",
    "auto_instrument",
    "context_overlay",
    "get_current_span",
    "add_span_attribute",
    "chat_span",
    "execute_tool_span",
    "invoke_agent_span",
    "TelemetryMiddleware",
]

try:
    from sap_cloud_sdk.core.telemetry.middleware import StarletteIASTelemetryMiddleware

    __all__ += ["StarletteIASTelemetryMiddleware"]
except ImportError:
    pass
