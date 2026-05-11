"""SAP Cloud SDK for Python - Agent Gateway module.

The Agent Gateway SDK enables agents to discover and invoke MCP tools.
It automatically detects agent type (LoB vs Customer) based on credential
file presence.

- LoB agents: Use BTP Destination Service, require tenant_subdomain and user_token
- Customer agents: Use file-based credentials with mTLS authentication

Usage (LoB agent):
    from sap_cloud_sdk.agentgateway import create_client

    agw_client = create_client(tenant_subdomain="my-tenant")

    # Discover tools
    tools = await agw_client.list_mcp_tools()
    for tool in tools:
        print(f"{tool.namespaced_name}: {tool.description}")

    # Invoke a tool
    # Note: kwargs like "order_id" are tool-specific input parameters.
    # Check tool.input_schema for expected parameters for each tool.
    result = await agw_client.call_mcp_tool(
        tool=tools[0],
        user_token="user-jwt",
        order_id="12345",  # example tool-specific parameter
    )

Usage (Customer agent):
    from sap_cloud_sdk.agentgateway import create_client

    agw_client = create_client()

    # Discover tools (reads all servers from credentials integrationDependencies)
    tools = await agw_client.list_mcp_tools()

    # Invoke a tool
    # Note: kwargs like "cost_center" are tool-specific input parameters.
    # Check tool.input_schema for expected parameters for each tool.
    result = await agw_client.call_mcp_tool(
        tool=tools[0],
        user_token="user-jwt",
        cost_center="1000",  # example tool-specific parameter
    )

    # Convert to LangChain tools
    from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain

    langchain_tools = [
        mcp_tool_to_langchain(t, agw_client.call_mcp_tool, get_user_token)
        for t in tools
    ]
"""

from sap_cloud_sdk.agentgateway._models import MCPTool
from sap_cloud_sdk.agentgateway.agw_client import create_client, AgentGatewayClient
from sap_cloud_sdk.agentgateway.exceptions import (
    AgentGatewaySDKError,
    MCPServerNotFoundError,
)


__all__ = [
    # Factory function
    "create_client",
    # Client class
    "AgentGatewayClient",
    # Data models
    "MCPTool",
    # Exceptions
    "AgentGatewaySDKError",
    "MCPServerNotFoundError",
]
