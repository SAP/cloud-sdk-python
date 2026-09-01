"""Compatibility shims for reading MCP result objects across mcp 1.x and 2.x."""

from typing import Any


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


def mcp_is_error(result: Any) -> bool:
    """Return the tool-call error flag across mcp 1.x/2.x, defaulting to False."""
    flag = getattr(result, "is_error", None)
    if flag is None:
        flag = getattr(result, "isError", None)
    return bool(flag)
