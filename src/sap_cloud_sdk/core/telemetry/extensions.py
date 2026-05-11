"""
Extension telemetry utilities for OpenTelemetry context propagation.

This module provides utilities for setting extension context in OTel baggage,
enabling propagation of extension metadata to downstream MCP servers via
HTTP headers.

When an agent calls an extension tool or hook, the extension context
(capability_id, extension_name, extension_type, extension_id,
extension_version, item_name) is set in OTel baggage. The baggage is
automatically propagated via the ``baggage`` HTTP header when using
instrumented HTTP clients (enabled by auto_instrument()).

MCP servers can extract this context from the incoming request's baggage header
to identify extension calls and add appropriate attributes to their spans.

Additionally provides:
- Source info resolution from ``ExtensionSourceInfo`` dataclass or plain dicts.
- Instrumented wrappers for extension tool and hook calls.
- ContextVar-based metrics accumulators for tool/hook call duration tracking.
- A summary span emitter for aggregate extension operation metrics.
- A logging filter that injects extension context into log records.
"""

import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from enum import Enum
from typing import Any, Generator

from opentelemetry import baggage, trace
from opentelemetry.context import attach, detach, get_current

logger = logging.getLogger(__name__)

# Extension attribute/baggage keys
# Same keys are used for both OTel baggage (HTTP propagation) and span
# attributes, providing a unified ``sap.extension.*`` prefix.
ATTR_IS_EXTENSION = "sap.extension.isExtension"
ATTR_EXTENSION_TYPE = "sap.extension.extensionType"
ATTR_CAPABILITY_ID = "sap.extension.capabilityId"
ATTR_EXTENSION_ID = "sap.extension.extensionId"
ATTR_EXTENSION_NAME = "sap.extension.extensionName"
ATTR_EXTENSION_VERSION = "sap.extension.extensionVersion"
ATTR_EXTENSION_ITEM_NAME = "sap.extension.extension.item.name"
ATTR_EXTENSION_URL = "sap.extension.extensionUrl"
ATTR_SOLUTION_ID = "sap.extension.solution_id"


class ExtensionType(str, Enum):
    """Type of extension being executed.

    Used to distinguish between different extension mechanisms:
    - TOOL: MCP tool call
    - INSTRUCTION: Instruction/prompt injection
    - HOOK: Hook call
    """

    TOOL = "tool"
    INSTRUCTION = "instruction"
    HOOK = "hook"


@contextmanager
def extension_context(
    capability_id: str,
    extension_name: str,
    extension_type: ExtensionType,
    extension_id: str = "",
    extension_version: str = "",
    item_name: str = "",
    extension_url: str = "",
    solution_id: str = "",
) -> Generator[None, None, None]:
    """Set extension context in OTel baggage for propagation.

    This context manager sets baggage values that are automatically
    propagated via HTTP headers when using instrumented HTTP clients.
    MCP servers receiving requests within this context will see the
    extension metadata in the ``baggage`` header.

    Baggage keys set:
    - ``sap.extension.isExtension``: ``"true"``
    - ``sap.extension.extensionType``: The extension type
    - ``sap.extension.capabilityId``: The capability ID
    - ``sap.extension.extensionId``: The extension UUID
    - ``sap.extension.extensionName``: The extension name
    - ``sap.extension.extensionVersion``: The extension version
    - ``sap.extension.extension.item.name``: The tool or hook name
    - ``sap.extension.extensionUrl``: The extension URL (when provided)
    - ``sap.extension.solution_id``: The solution ID (when provided)

    Args:
        capability_id: The capability ID for the extension
            (e.g. ``"default"``).
        extension_name: The name of the extension
            (e.g. ``"ServiceNow Extension"``).
        extension_type: The type of extension (tool, instruction, or hook).
        extension_id: The unique identifier (UUID) of the extension.
        extension_version: The version of the extension (e.g. ``"1"``).
        item_name: The name of the specific tool or hook being called.
        extension_url: The build extension URL (empty string if not available).
        solution_id: The build solution ID (empty string if not available).

    Yields:
        None. The context is active for the duration of the with block.

    Example:
        ```python
        from sap_cloud_sdk.core.telemetry import (
            extension_context,
            ExtensionType,
        )

        with extension_context(
            "default",
            "ServiceNow Extension",
            ExtensionType.TOOL,
            extension_id="a1b2c3d4-...",
            extension_version="1",
            item_name="create_ticket",
            solution_id="my-solution-42",
        ):
            result = await mcp_client.call_tool("create_ticket", args)
        ```

    Note:
        Requires ``auto_instrument()`` to be called at application startup
        for automatic baggage header injection into HTTP requests.
    """
    ctx = get_current()
    ctx = baggage.set_baggage(ATTR_IS_EXTENSION, "true", context=ctx)
    ctx = baggage.set_baggage(ATTR_EXTENSION_TYPE, extension_type.value, context=ctx)
    ctx = baggage.set_baggage(ATTR_CAPABILITY_ID, capability_id, context=ctx)
    ctx = baggage.set_baggage(ATTR_EXTENSION_ID, extension_id, context=ctx)
    ctx = baggage.set_baggage(ATTR_EXTENSION_NAME, extension_name, context=ctx)
    ctx = baggage.set_baggage(ATTR_EXTENSION_VERSION, extension_version, context=ctx)
    ctx = baggage.set_baggage(ATTR_EXTENSION_ITEM_NAME, item_name, context=ctx)
    if extension_url:
        ctx = baggage.set_baggage(ATTR_EXTENSION_URL, extension_url, context=ctx)
    if solution_id:
        ctx = baggage.set_baggage(ATTR_SOLUTION_ID, solution_id, context=ctx)

    token = attach(ctx)
    try:
        yield
    finally:
        detach(token)


def get_extension_context() -> dict[str, Any] | None:
    """Extract extension context from the current OTel baggage.

    Use this function in MCP servers or downstream services to detect
    if the current request is an extension call and retrieve the
    extension metadata.

    Returns:
        A dictionary with extension metadata if in an extension context:

        - ``is_extension``: ``True``
        - ``extension_type``: The extension type string
        - ``capability_id``: The capability ID
        - ``extension_id``: The extension UUID
        - ``extension_name``: The extension name
        - ``extension_version``: The extension version string
        - ``item_name``: The tool or hook name
        - ``extension_url``: The extension URL (empty string if not set)
        - ``solution_id``: The solution ID (empty string if not set)

        Returns ``None`` if not in an extension context.

    Example:
        ```python
        from sap_cloud_sdk.core.telemetry import get_extension_context

        ext_ctx = get_extension_context()
        if ext_ctx:
            logger.info(f"Extension call: {ext_ctx['extension_name']}")
        ```
    """
    is_extension = baggage.get_baggage(ATTR_IS_EXTENSION)
    if is_extension != "true":
        return None

    return {
        "is_extension": True,
        "extension_type": baggage.get_baggage(ATTR_EXTENSION_TYPE),
        "capability_id": baggage.get_baggage(ATTR_CAPABILITY_ID),
        "extension_id": baggage.get_baggage(ATTR_EXTENSION_ID),
        "extension_name": baggage.get_baggage(ATTR_EXTENSION_NAME),
        "extension_version": baggage.get_baggage(ATTR_EXTENSION_VERSION),
        "item_name": baggage.get_baggage(ATTR_EXTENSION_ITEM_NAME),
        "extension_url": baggage.get_baggage(ATTR_EXTENSION_URL) or "",
        "solution_id": baggage.get_baggage(ATTR_SOLUTION_ID) or "",
    }


# ---------------------------------------------------------------------------
# Summary span attribute constants
# ---------------------------------------------------------------------------

ATTR_SUMMARY_TOTAL_OPERATION_COUNT = "sap.extension.summary.totalOperationCount"
ATTR_SUMMARY_TOTAL_DURATION_MS = "sap.extension.summary.totalDurationMs"
ATTR_SUMMARY_TOOL_CALL_COUNT = "sap.extension.summary.toolCallCount"
ATTR_SUMMARY_HOOK_CALL_COUNT = "sap.extension.summary.hookCallCount"
ATTR_SUMMARY_HAS_INSTRUCTION = "sap.extension.summary.hasInstruction"

# ---------------------------------------------------------------------------
# Private state
# ---------------------------------------------------------------------------

_tracer = trace.get_tracer("sap.cloud_sdk.extension")

_tool_call_durations: ContextVar[list[float]] = ContextVar("ext_tool_call_durations")
_hook_call_durations: ContextVar[list[float]] = ContextVar("ext_hook_call_durations")

# Mapping: OTel baggage key -> LogRecord attribute name (for log filter)
_BAGGAGE_LOG_FIELDS = [
    (ATTR_IS_EXTENSION, "ext_is_extension"),
    (ATTR_EXTENSION_TYPE, "ext_extension_type"),
    (ATTR_CAPABILITY_ID, "ext_capability_id"),
    (ATTR_EXTENSION_ID, "ext_extension_id"),
    (ATTR_EXTENSION_NAME, "ext_extension_name"),
    (ATTR_EXTENSION_VERSION, "ext_extension_version"),
    (ATTR_EXTENSION_ITEM_NAME, "ext_item_name"),
    (ATTR_EXTENSION_URL, "ext_extension_url"),
    (ATTR_SOLUTION_ID, "ext_solution_id"),
]


# ---------------------------------------------------------------------------
# Source info resolution
# ---------------------------------------------------------------------------


def resolve_source_info(
    key: str,
    source_mapping: dict[str, Any] | None,
    fallback_name: str,
) -> tuple[str, str, str, str, str]:
    """Resolve extension name, id, version, url, and solution_id from a source mapping.

    Source mapping values may be ``ExtensionSourceInfo`` dataclass instances
    (with attributes ``extension_name``, ``extension_id``,
    ``extension_version``, ``extension_url``, ``solution_id``) or plain dicts
    with camelCase keys (``extensionName``, ``extensionId``,
    ``extensionVersion``, ``extensionUrl``, ``solutionId``).

    Falls back to *fallback_name* for the name and empty strings for other
    fields when the key is not found in the mapping.

    Args:
        key: Lookup key in the source mapping (e.g. prefixed tool name or
            hook ID).
        source_mapping: Mapping of keys to source info objects or dicts.
            May be ``None``.
        fallback_name: Name to use when the key is not found or the resolved
            name is empty.

    Returns:
        Tuple of ``(extension_name, extension_id, extension_version, extension_url, solution_id)``.
    """
    info = (source_mapping or {}).get(key)
    if info is None:
        return (fallback_name or "unknown", "", "", "", "")
    # SDK ExtensionSourceInfo dataclass (duck-typed to avoid circular import)
    if hasattr(info, "extension_name"):
        return (
            info.extension_name or fallback_name or "unknown",
            info.extension_id or "",
            str(info.extension_version) if info.extension_version else "",
            getattr(info, "extension_url", "") or "",
            getattr(info, "solution_id", "") or "",
        )
    # Plain dict with camelCase keys (older SDK or manual construction)
    if isinstance(info, dict):
        return (
            info.get("extensionName") or fallback_name or "unknown",
            info.get("extensionId") or "",
            str(info.get("extensionVersion", "")) or "",
            info.get("extensionUrl") or "",
            info.get("solutionId") or "",
        )
    return (fallback_name or "unknown", "", "", "", "")


# ---------------------------------------------------------------------------
# Span attribute builder
# ---------------------------------------------------------------------------


def build_extension_span_attributes(
    extension_name: str,
    extension_id: str,
    extension_version: str,
    ext_type: ExtensionType,
    capability: str,
    item_name: str,
    extension_url: str = "",
    solution_id: str = "",
) -> dict[str, Any]:
    """Build the full set of ``sap.extension.*`` span attributes.

    Args:
        extension_name: Human-readable name of the extension.
        extension_id: Unique identifier (UUID) of the extension.
        extension_version: Version of the extension.
        ext_type: The extension type (tool, instruction, or hook).
        capability: Extension capability ID (e.g. ``"default"``).
        item_name: Name of the specific tool or hook being called.
        extension_url: Build extension URL (empty string if not available).
        solution_id: Build solution ID (empty string if not available).

    Returns:
        Dict with all ``sap.extension.*`` attribute keys.
    """
    attrs: dict[str, Any] = {
        ATTR_IS_EXTENSION: True,
        ATTR_EXTENSION_TYPE: ext_type.value,
        ATTR_CAPABILITY_ID: capability,
        ATTR_EXTENSION_ID: extension_id,
        ATTR_EXTENSION_NAME: extension_name,
        ATTR_EXTENSION_VERSION: extension_version,
        ATTR_EXTENSION_ITEM_NAME: item_name,
    }
    if extension_url:
        attrs[ATTR_EXTENSION_URL] = extension_url
    if solution_id:
        attrs[ATTR_SOLUTION_ID] = solution_id
    return attrs


# ---------------------------------------------------------------------------
# Tool call metrics accumulator
# ---------------------------------------------------------------------------


def reset_tool_call_metrics() -> None:
    """Initialise a fresh accumulator for tool call durations.

    Call this at the **start** of ``execute()``, before any hooks or
    ``agent.run()`` invocations.
    """
    _tool_call_durations.set([])


def get_tool_call_metrics() -> tuple[int, float]:
    """Return ``(call_count, total_duration_ms)`` for tool calls since reset.

    Returns ``(0, 0.0)`` if ``reset_tool_call_metrics`` was never called.
    """
    durations = _tool_call_durations.get([])
    return len(durations), sum(durations) * 1000


def record_tool_call_duration(duration: float) -> None:
    """Record the wall-clock duration (seconds) of a single tool call.

    Appends to the ContextVar accumulator.  Silently no-ops if
    ``reset_tool_call_metrics`` was never called.

    Args:
        duration: Duration in **seconds** (e.g. from ``time.monotonic()``
            difference).
    """
    durations = _tool_call_durations.get(None)
    if durations is not None:
        durations.append(duration)


# ---------------------------------------------------------------------------
# Hook call metrics accumulator
# ---------------------------------------------------------------------------


def reset_hook_call_metrics() -> None:
    """Initialise a fresh accumulator for hook call durations.

    Call this at the **start** of ``execute()``, before any hooks or
    ``agent.run()`` invocations.
    """
    _hook_call_durations.set([])


def get_hook_call_metrics() -> tuple[int, float]:
    """Return ``(call_count, total_duration_ms)`` for hook calls since reset.

    Returns ``(0, 0.0)`` if ``reset_hook_call_metrics`` was never called.
    """
    durations = _hook_call_durations.get([])
    return len(durations), sum(durations) * 1000


def record_hook_call_duration(duration: float) -> None:
    """Record the wall-clock duration (seconds) of a single hook call.

    Appends to the ContextVar accumulator.  Silently no-ops if
    ``reset_hook_call_metrics`` was never called.

    Args:
        duration: Duration in **seconds** (e.g. from ``time.monotonic()``
            difference).
    """
    durations = _hook_call_durations.get(None)
    if durations is not None:
        durations.append(duration)


# ---------------------------------------------------------------------------
# Instrumented extension tool call
# ---------------------------------------------------------------------------


async def call_extension_tool(
    mcp_client: Any,
    tool_name: str,
    args: dict[str, Any],
    extension_name: str,
    capability: str = "default",
    source_mapping: dict[str, Any] | None = None,
    tool_prefix: str = "",
) -> Any:
    """Call an MCP tool with telemetry instrumentation.

    Wraps the tool call with ``extension_context`` (sets OTel baggage for
    downstream propagation) and creates an explicit tracer span with all
    seven ``sap.extension.*`` attributes so the call is visible in
    agent-side traces.

    Args:
        mcp_client: The MCP client session connected to the tool's server.
            Must have an async ``call_tool(name, args)`` method.
        tool_name: The raw MCP tool name (before any prefixing).
        args: Dictionary of arguments to pass to the tool.
        extension_name: Human-readable name of the extension.  Used as
            fallback when *source_mapping* does not contain the tool.
        capability: Extension capability ID (default: ``"default"``).
        source_mapping: Optional mapping of prefixed tool names to source
            info objects (from ``ext_impl.source.tools``).
        tool_prefix: The tool prefix (e.g. ``"sap_mcp_servicenow_v1_"``).
            Used to reconstruct the lookup key for *source_mapping*.

    Returns:
        The tool's response from the MCP server.
    """
    lookup_key = tool_prefix + tool_name if tool_prefix else tool_name

    resolved_name, resolved_id, resolved_version, resolved_url, resolved_solution_id = (
        resolve_source_info(lookup_key, source_mapping, extension_name)
    )

    attrs = build_extension_span_attributes(
        resolved_name,
        resolved_id,
        resolved_version,
        ExtensionType.TOOL,
        capability,
        tool_name,
        extension_url=resolved_url,
        solution_id=resolved_solution_id,
    )

    t0 = time.monotonic()
    try:
        with (
            extension_context(
                capability_id=capability,
                extension_name=resolved_name,
                extension_type=ExtensionType.TOOL,
                extension_id=resolved_id,
                extension_version=resolved_version,
                item_name=tool_name,
                extension_url=resolved_url,
                solution_id=resolved_solution_id,
            ),
            _tracer.start_as_current_span(
                f"extension_tool {tool_name}",
                attributes=attrs,
            ),
        ):
            logger.info("Calling extension tool: %s", tool_name)
            result = await mcp_client.call_tool(tool_name, args)
            logger.info("Extension tool completed: %s", tool_name)
            return result
    finally:
        record_tool_call_duration(time.monotonic() - t0)


# ---------------------------------------------------------------------------
# Instrumented extension hook call
# ---------------------------------------------------------------------------


async def call_extension_hook(
    extensibility_client: Any,
    hook: Any,
    payload: Any,
    extension_name: str,
    capability: str = "default",
    source_mapping: dict[str, Any] | None = None,
    hook_id: str = "",
) -> Any:
    """Call an extension hook with telemetry instrumentation.

    Wraps the hook call with ``extension_context`` (sets OTel baggage for
    downstream propagation) and creates an explicit tracer span with all
    seven ``sap.extension.*`` attributes so the call is visible in
    agent-side traces.

    Args:
        extensibility_client: The extensibility client.  Must have an async
            ``call_hook(hook, payload)`` method.
        hook: The hook object to invoke.  If it has a ``name`` attribute,
            that is used as the ``item_name`` in telemetry.
        payload: The payload to send to the hook endpoint.
        extension_name: Human-readable name of the extension.  Used as
            fallback when *source_mapping* does not contain the hook.
        capability: Extension capability ID (default: ``"default"``).
        source_mapping: Optional mapping of hook IDs to source info
            objects (from ``ext_impl.source.hooks``).
        hook_id: The unique hook ``id`` (UUID), used as lookup key in
            *source_mapping*.

    Returns:
        The hook's response.
    """
    resolved_name, resolved_id, resolved_version, resolved_url, resolved_solution_id = (
        resolve_source_info(hook_id, source_mapping, extension_name)
    )

    item_name = getattr(hook, "name", None) or hook_id

    attrs = build_extension_span_attributes(
        resolved_name,
        resolved_id,
        resolved_version,
        ExtensionType.HOOK,
        capability,
        item_name,
        extension_url=resolved_url,
        solution_id=resolved_solution_id,
    )

    t0 = time.monotonic()
    try:
        with (
            extension_context(
                capability_id=capability,
                extension_name=resolved_name,
                extension_type=ExtensionType.HOOK,
                extension_id=resolved_id,
                extension_version=resolved_version,
                item_name=item_name,
                extension_url=resolved_url,
                solution_id=resolved_solution_id,
            ),
            _tracer.start_as_current_span(
                f"extension_hook {item_name}",
                attributes=attrs,
            ),
        ):
            logger.info("Calling extension hook: %s", item_name)
            result = await extensibility_client.call_hook(hook, payload)
            logger.info("Extension hook completed: %s", item_name)
            return result
    finally:
        record_hook_call_duration(time.monotonic() - t0)


# ---------------------------------------------------------------------------
# Aggregate summary span
# ---------------------------------------------------------------------------


def emit_extensions_summary_span(
    *,
    tool_call_count: int,
    hook_call_count: int,
    has_instruction: bool,
    total_duration_ms: float,
) -> None:
    """Emit a sibling summary span with aggregate extension metrics.

    Creates a zero-duration ``agent_extensions_summary`` span carrying
    aggregate counts and timing for all extension operations performed
    during one agent execution.  The span is created via ``start_span``
    (not ``start_as_current_span``) and immediately ended, so it appears
    as a **sibling** of the individual ``extension_tool`` /
    ``extension_hook`` spans — it never becomes a parent or alters the
    existing span hierarchy.

    Call this **once** at the end of the agent's ``execute()`` method,
    after all extension operations have completed.

    Args:
        tool_call_count: Number of extension tool calls made.
        hook_call_count: Number of hook calls executed (pre + post).
        has_instruction: Whether an extension instruction was injected
            into the system prompt.
        total_duration_ms: Wall-clock sum (milliseconds) of all extension
            operations.
    """
    total = tool_call_count + hook_call_count + (1 if has_instruction else 0)
    attrs = {
        ATTR_SUMMARY_TOTAL_OPERATION_COUNT: total,
        ATTR_SUMMARY_TOTAL_DURATION_MS: total_duration_ms,
        ATTR_SUMMARY_TOOL_CALL_COUNT: tool_call_count,
        ATTR_SUMMARY_HOOK_CALL_COUNT: hook_call_count,
        ATTR_SUMMARY_HAS_INSTRUCTION: has_instruction,
    }
    span = _tracer.start_span("agent_extensions_summary", attributes=attrs)
    span.end()


# ---------------------------------------------------------------------------
# Log filter
# ---------------------------------------------------------------------------


class ExtensionContextLogFilter(logging.Filter):
    """Logging filter that injects extension context from OTel baggage.

    When a log statement is emitted inside an ``extension_context()`` block,
    the filter reads the seven ``sap.extension.*`` baggage values from the
    current OTel context and sets them as extra attributes on the
    ``LogRecord``.  Combined with a JSON formatter these attributes are
    serialised into the JSON log line.

    When the current context has **no** extension baggage, the filter does
    **not** add ``ext_*`` attributes, keeping non-extension log lines clean.

    .. warning::

        The filter **must** be added to the **handler**, not the logger.
        Logger-level filters are only checked in ``Logger.handle()``, which
        is **not** called when a child logger's record propagates up via
        ``callHandlers()``.  Handler-level filters are checked in
        ``Handler.handle()``, which runs for every record regardless of
        origin.

    Example::

        handler = logging.StreamHandler()
        handler.addFilter(ExtensionContextLogFilter())
        logging.getLogger().addHandler(handler)
    """

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_current()
        is_extension = baggage.get_baggage(ATTR_IS_EXTENSION, context=ctx)
        if is_extension:
            for baggage_key, attr_name in _BAGGAGE_LOG_FIELDS:
                value = baggage.get_baggage(baggage_key, context=ctx)
                setattr(record, attr_name, value or "")
        return True
