"""Compatibility shims for reading MCP result objects across mcp 1.x and 2.x."""

from typing import Any

try:
    from mcp.shared.exceptions import McpError
except ImportError:
    from mcp.shared.exceptions import MCPError as McpError  # ty: ignore[unresolved-import]


def mcp_server_name(init_result: Any) -> str | None:
    """Return ``serverInfo.name`` / ``server_info.name`` if present, else None."""
    info = getattr(init_result, "server_info", None)
    if info is None:
        info = getattr(init_result, "serverInfo", None)
    return getattr(info, "name", None) if info is not None else None


def mcp_input_schema(tool: Any) -> dict[str, Any]:
    """Return the tool's input schema across mcp 1.x/2.x, defaulting to {}."""
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)
    return schema or {}


def mcp_output_schema(tool: Any) -> dict[str, Any] | None:
    """Return the tool's output schema across mcp 1.x/2.x, or None if absent.

    MCP Builder tools advertise an ``outputSchema`` describing the shape of the
    structured result. The mcp client exposes it as ``output_schema`` (snake) or
    ``outputSchema`` (camel) depending on version. Returns None when the tool has
    no output schema so callers can distinguish "no schema" from an empty one.
    """
    schema = getattr(tool, "output_schema", None)
    if schema is None:
        schema = getattr(tool, "outputSchema", None)
    return schema or None


def mcp_is_error(result: Any) -> bool:
    """Return the tool-call error flag across mcp 1.x/2.x, defaulting to False."""
    flag = getattr(result, "is_error", None)
    if flag is None:
        flag = getattr(result, "isError", None)
    return bool(flag)


def find_mcp_error(exc: BaseException) -> "McpError | None":
    """Return the first ``McpError`` carried by ``exc``, or None.

    A protocol error (JSON-RPC ``error``) raised by ``session.call_tool`` surfaces
    either as a bare ``McpError`` or, because the mcp client runs inside anyio task
    groups, wrapped in a (possibly nested) ``BaseExceptionGroup``. This walks the
    group tree and returns the first ``McpError`` leaf so callers can surface its
    code+message. Returns None when no ``McpError`` is present, so the caller can
    defer to its generic error handling.
    """
    if isinstance(exc, McpError):
        return exc
    if isinstance(exc, BaseExceptionGroup):
        for inner in exc.exceptions:
            found = find_mcp_error(inner)
            if found is not None:
                return found
    return None
