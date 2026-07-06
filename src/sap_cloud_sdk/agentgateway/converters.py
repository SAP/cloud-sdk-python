"""Reference converter for MCPTool to LangChain StructuredTool.

This module provides a sample converter as a starting point.
End-users have full flexibility to write their own converters with
custom tool naming, argument schemas, or framework integrations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from pydantic import Field, create_model

from sap_cloud_sdk.agentgateway._models import MCPTool

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool

_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _resolve_type(json_type: Any) -> tuple[type, bool]:
    """Return (python_type, is_nullable) from a JSON Schema ``type`` value.

    Handles both the plain-string form (``"integer"``) and the array form
    (``["integer", "null"]``).  Unknown or missing types map to ``Any``.
    """
    if isinstance(json_type, list):
        nullable = "null" in json_type
        scalar = next((t for t in json_type if t != "null"), None)
        return _JSON_TYPE_MAP.get(scalar, Any), nullable
    return _JSON_TYPE_MAP.get(json_type, Any), False


def mcp_tool_to_langchain(
    mcp_tool: MCPTool,
    call_tool: Callable,
    get_user_token: Callable[[], str],
    *,
    omit_none: bool = True,
) -> StructuredTool:
    """Convert MCPTool to LangChain StructuredTool.

    This is a reference implementation. End-users can write their own
    converter with custom naming, argument handling, or framework bindings.

    Args:
        mcp_tool: MCPTool object from list_mcp_tools().
        call_tool: Callable to invoke the MCP tool (e.g., agw_client.call_mcp_tool).
        get_user_token: Callable that returns the user's JWT token.
        omit_none: If True (default), optional parameters with a None value are not
            forwarded to call_tool. Set to False to forward None values explicitly.

    Returns:
        LangChain StructuredTool that invokes the MCP tool.

    Example:
        ```python
        from sap_cloud_sdk.agentgateway import create_client
        from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain

        agw_client = create_client(tenant_subdomain="my-tenant")
        tools = await agw_client.list_mcp_tools()

        # Convert to LangChain tools
        langchain_tools = [
            mcp_tool_to_langchain(
                t,
                agw_client.call_mcp_tool,
                get_user_token=lambda: request.headers["Authorization"],
            )
            for t in tools
        ]

        # Use with LangChain agent
        llm_with_tools = llm.bind_tools(langchain_tools)
        ```
    """
    try:
        from langchain_core.tools import StructuredTool
    except ImportError:
        raise ImportError(
            "langchain-core is required for mcp_tool_to_langchain. "
            "Install it with: pip install sap-cloud-sdk[langchain]"
        ) from None

    async def run(**kwargs) -> str:
        resolved = (
            {k: v for k, v in kwargs.items() if v is not None} if omit_none else kwargs
        )
        return await call_tool(
            mcp_tool,
            user_token=get_user_token,
            **resolved,
        )

    # Build args schema from input_schema
    properties = mcp_tool.input_schema.get("properties", {})
    required = set(mcp_tool.input_schema.get("required", []))
    fields: dict[str, Any] = {}
    for k, v in properties.items():
        py_type, type_nullable = _resolve_type(v.get("type"))
        optional = k not in required
        if optional or type_nullable:
            fields[k] = (py_type | None, Field(default=None))
        else:
            fields[k] = (py_type, ...)
    args_schema = create_model(f"{mcp_tool.name}_args", **fields) if fields else None

    return StructuredTool.from_function(
        coroutine=run,
        name=mcp_tool.name,
        description=mcp_tool.description,
        args_schema=args_schema,
    )
