"""Compatibility shims for reading MCP result objects across mcp 1.x and 2.x."""

from typing import Any

try:
    from mcp.shared.exceptions import McpError
except ImportError:
    from mcp.shared.exceptions import MCPError as McpError  # ty: ignore[unresolved-import]


def make_mcp_error(code: int, message: str) -> "McpError":
    """Construct an ``McpError`` with ``.error.code`` / ``.error.message`` set, across
    mcp 1.x and 2.x.

    The constructor signature changed between majors:

    - **mcp 1.x:** ``McpError(ErrorData(code=..., message=...))`` — a single ``ErrorData``.
    - **mcp 2.x:** ``MCPError(code, message, data=None)`` — positional ``code``/``message``
      (and the class was renamed ``McpError`` → ``MCPError``; see the import shim above).

    Both result in an exception exposing ``exc.error.code`` and ``exc.error.message``,
    which is what the SDK reads when surfacing a protocol error as an
    ``AgentGatewayServerError``. This helper hides the signature difference so callers
    (and tests) do not need to branch on the installed mcp major.
    """
    try:
        # mcp 2.x: positional code + message. (ty type-checks against whichever mcp
        # major is installed; the 1.x ErrorData signature makes this look wrong even
        # though it is correct at runtime under v2, so suppress both shape diagnostics.)
        return McpError(code, message)  # ty: ignore[invalid-argument-type, too-many-positional-arguments]
    except TypeError:
        # mcp 1.x: a single ErrorData payload.
        from mcp.types import ErrorData

        return McpError(ErrorData(code=code, message=message))


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


def find_malformed_result_error(exc: BaseException) -> "AttributeError | None":
    """Return the first "result was None" ``AttributeError`` carried by ``exc``, else None.

    The mcp client's ``ClientSession.call_tool`` does an unguarded ``if not
    result.isError:`` (mcp 1.x; renamed ``is_error`` in 2.x). When something upstream
    yields ``None`` instead of a ``CallToolResult``, that line raises
    ``AttributeError: 'NoneType' object has no attribute 'isError'`` *inside*
    ``call_tool`` — before the SDK ever gets a value back to None-check. This matches
    that AttributeError (by the ``isError`` / ``is_error`` attribute name) so the caller
    can surface a clean error instead of leaking ``'NoneType' object has no attribute
    'isError'``.

    Walks ``BaseExceptionGroup`` trees (the mcp client runs inside anyio task groups),
    returning the first matching ``AttributeError`` leaf. Returns None for any other
    exception so the caller can defer to its generic handling.
    """
    if isinstance(exc, AttributeError):
        message = str(exc)
        if "isError" in message or "is_error" in message:
            return exc
        return None
    if isinstance(exc, BaseExceptionGroup):
        for inner in exc.exceptions:
            found = find_malformed_result_error(inner)
            if found is not None:
                return found
    return None
