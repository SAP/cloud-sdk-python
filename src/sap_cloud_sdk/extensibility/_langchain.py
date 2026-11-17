"""LangChain MCP tool call interceptor with extension telemetry instrumentation.

Provides :class:`ExtensionTelemetryInterceptor`, a ``ToolCallInterceptor``-compatible
class that wraps each MCP tool call with an OpenTelemetry span carrying all
``sap.extension.*`` attributes and sets OTel baggage for downstream propagation.

Usage::

    from sap_cloud_sdk.extensibility import ExtensionTelemetryInterceptor

    interceptor = ExtensionTelemetryInterceptor(ext_impl=ext_impl)
    client = MultiServerMCPClient(
        {server_name: server_config},
        tool_interceptors=[interceptor],
    )
    tools = await client.get_tools()
"""

import logging
import time
from typing import Any

from opentelemetry import trace
from sap_cloud_sdk.core.telemetry import (
    ATTR_CAPABILITY_ID,
    ATTR_EXTENSION_ID,
    ATTR_EXTENSION_ITEM_NAME,
    ATTR_EXTENSION_NAME,
    ATTR_EXTENSION_TYPE,
    ATTR_EXTENSION_VERSION,
    ATTR_IS_EXTENSION,
    ATTR_JOULE_STUDIO_GSID,
    ATTR_SOLUTION_ID,
    ExtensionType,
    extension_context,
    record_tool_call_duration,
)

logger = logging.getLogger(__name__)


def _get_tracer() -> trace.Tracer:
    """Get tracer lazily to avoid stale references from TracerProvider swaps."""
    return trace.get_tracer("sap.cloud_sdk.extension")


class ExtensionTelemetryInterceptor:
    """ToolCallInterceptor that adds sap.extension.* telemetry to MCP tool calls.

    Implements the ``langchain_mcp_adapters`` ``ToolCallInterceptor`` protocol.
    For each tool call, resolves per-tool source info (extension name, id,
    version, solution_id, joule_studio_gsid) via ``ext_impl.get_source_info_for_tool()``
    and creates an ``extension_tool <name>`` span with all ``sap.extension.*``
    attributes.  Also sets OTel baggage via ``extension_context`` for downstream
    propagation to the MCP server.

    Args:
        ext_impl: The extension implementation object from the extensibility client.
            Used to resolve per-tool source info via ``get_source_info_for_tool()``.
        capability: Extension capability name (default: ``"default"``).
    """

    def __init__(self, ext_impl: Any = None, capability: str = "default") -> None:
        self.ext_impl = ext_impl
        self.capability = capability

    async def __call__(self, request: Any, handler: Any) -> Any:
        """Intercept a tool call to add extension telemetry.

        Args:
            request: ``MCPToolCallRequest`` with ``name``, ``args``, etc.
            handler: Async callable to invoke the actual MCP tool call.

        Returns:
            The tool call result from the handler.
        """
        source_info = (
            self.ext_impl.get_source_info_for_tool(request.name)
            if self.ext_impl
            else None
        )

        resolved_name = source_info.extension_name if source_info else "unknown"
        resolved_id = source_info.extension_id if source_info else ""
        resolved_version = str(source_info.extension_version) if source_info else ""
        resolved_solution_id = (
            getattr(source_info, "solution_id", "") or "" if source_info else ""
        )
        resolved_joule_studio_gsid = (
            getattr(source_info, "joule_studio_gsid", "") or "" if source_info else ""
        )
        item_name = request.name

        _attrs: dict[str, Any] = {
            ATTR_IS_EXTENSION: True,
            ATTR_EXTENSION_TYPE: ExtensionType.TOOL.value,
            ATTR_CAPABILITY_ID: self.capability,
            ATTR_EXTENSION_ID: resolved_id,
            ATTR_EXTENSION_NAME: resolved_name,
            ATTR_EXTENSION_VERSION: resolved_version,
            ATTR_EXTENSION_ITEM_NAME: item_name,
            ATTR_SOLUTION_ID: resolved_solution_id,
            ATTR_JOULE_STUDIO_GSID: resolved_joule_studio_gsid,
        }

        t0 = time.monotonic()
        try:
            with (
                extension_context(
                    capability_id=self.capability,
                    extension_name=resolved_name,
                    extension_type=ExtensionType.TOOL,
                    extension_id=resolved_id,
                    extension_version=resolved_version,
                    item_name=item_name,
                    solution_id=resolved_solution_id,
                    joule_studio_gsid=resolved_joule_studio_gsid,
                ),
                _get_tracer().start_as_current_span(
                    f"extension_tool {item_name}",
                    attributes=_attrs,
                ),
            ):
                logger.info("Calling extension tool: %s", item_name)
                result = await handler(request)
                logger.info("Extension tool completed: %s", item_name)
                return result
        finally:
            record_tool_call_duration(time.monotonic() - t0)
