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
from sap_cloud_sdk.core.telemetry.extensions import (
    extension_context,
    get_extension_context,
    ExtensionType,
    ATTR_IS_EXTENSION,
    ATTR_EXTENSION_TYPE,
    ATTR_CAPABILITY_ID,
    ATTR_EXTENSION_ID,
    ATTR_EXTENSION_NAME,
    ATTR_EXTENSION_VERSION,
    ATTR_EXTENSION_ITEM_NAME,
    ATTR_EXTENSION_URL,
    ATTR_SOLUTION_ID,
    ATTR_SUMMARY_TOTAL_OPERATION_COUNT,
    ATTR_SUMMARY_TOTAL_DURATION_MS,
    ATTR_SUMMARY_TOOL_CALL_COUNT,
    ATTR_SUMMARY_HOOK_CALL_COUNT,
    ATTR_SUMMARY_HAS_INSTRUCTION,
    resolve_source_info,
    build_extension_span_attributes,
    reset_tool_call_metrics,
    get_tool_call_metrics,
    record_tool_call_duration,
    reset_hook_call_metrics,
    get_hook_call_metrics,
    record_hook_call_duration,
    call_extension_tool,
    call_extension_hook,
    emit_extensions_summary_span,
    ExtensionContextLogFilter,
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
    "extension_context",
    "get_extension_context",
    "ExtensionType",
    "ATTR_IS_EXTENSION",
    "ATTR_EXTENSION_TYPE",
    "ATTR_CAPABILITY_ID",
    "ATTR_EXTENSION_ID",
    "ATTR_EXTENSION_NAME",
    "ATTR_EXTENSION_VERSION",
    "ATTR_EXTENSION_ITEM_NAME",
    "ATTR_EXTENSION_URL",
    "ATTR_SOLUTION_ID",
    "ATTR_SUMMARY_TOTAL_OPERATION_COUNT",
    "ATTR_SUMMARY_TOTAL_DURATION_MS",
    "ATTR_SUMMARY_TOOL_CALL_COUNT",
    "ATTR_SUMMARY_HOOK_CALL_COUNT",
    "ATTR_SUMMARY_HAS_INSTRUCTION",
    "resolve_source_info",
    "build_extension_span_attributes",
    "reset_tool_call_metrics",
    "get_tool_call_metrics",
    "record_tool_call_duration",
    "reset_hook_call_metrics",
    "get_hook_call_metrics",
    "record_hook_call_duration",
    "call_extension_tool",
    "call_extension_hook",
    "emit_extensions_summary_span",
    "ExtensionContextLogFilter",
    "TelemetryMiddleware",
]

try:
    from sap_cloud_sdk.core.telemetry.middleware import StarletteIASTelemetryMiddleware

    __all__ += ["StarletteIASTelemetryMiddleware"]
except ImportError:
    pass
