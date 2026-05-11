"""Converters for MCPTool to framework-specific tools.

This module provides converters to transform MCPTool objects into
tools compatible with popular agent frameworks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from pydantic import create_model

from sap_cloud_sdk.agentgateway._models import MCPTool

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool


def mcp_tool_to_langchain(
    mcp_tool: MCPTool,
    call_tool: Callable,
    get_user_token: Callable[[], str],
) -> StructuredTool:
    """Convert MCPTool to LangChain StructuredTool.

    Args:
        mcp_tool: MCPTool object from list_mcp_tools().
        call_tool: Callable to invoke the MCP tool (e.g., agw_client.call_mcp_tool).
        get_user_token: Callable that returns the user's JWT token.

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
        return await call_tool(
            mcp_tool,
            user_token=get_user_token,
            **kwargs,
        )

    # Build args schema from input_schema
    properties = mcp_tool.input_schema.get("properties", {})
    fields: dict[str, Any] = {k: (str, ...) for k in properties}
    args_schema = (
        create_model(f"{mcp_tool.namespaced_name}_args", **fields) if fields else None
    )

    return StructuredTool.from_function(
        coroutine=run,
        name=mcp_tool.namespaced_name,
        description=mcp_tool.description,
        args_schema=args_schema,
    )
