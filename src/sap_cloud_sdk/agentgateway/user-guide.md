# Agent Gateway User Guide

This module provides a framework-agnostic client for discovering and invoking MCP tools via SAP Agent Gateway. It automatically detects the agent type (LoB vs Customer) based on credential file presence and handles authentication accordingly.

## Installation

This package is part of the SAP Cloud SDK for Python. Import and use it directly in your application.

For LangChain integration, install the optional extra:

```bash
pip install sap-cloud-sdk[langchain]
```

## Quick Start

### Customer Agent Flow

Customer agents use file-based credentials with mTLS authentication. MCP servers are read from `integrationDependencies` in the credentials file.

```python
from sap_cloud_sdk.agentgateway import create_client

agw_client = create_client()

# Discover tools (reads all servers from credentials integrationDependencies)
tools = await agw_client.list_mcp_tools()

for tool in tools:
    print(f"{tool.namespaced_name}: {tool.description}")

# Invoke a tool with user principal propagation
result = await agw_client.call_mcp_tool(
    tool=tools[0],
    user_token="user-jwt",
    cost_center="1000",
)

```

### LoB Agent Flow

LoB agents use BTP Destination Service for credential management. Tools are auto-discovered from destination fragments.

```python
from sap_cloud_sdk.agentgateway import create_client

agw_client = create_client(tenant_subdomain="my-tenant")

# Discover tools (auto-discovered from destination fragments)
tools = await agw_client.list_mcp_tools()

# Invoke a tool (user_token required for principal propagation)
result = await agw_client.call_mcp_tool(
    tool=tools[0],
    user_token="user-jwt",
    order_id="12345",
)
```

### LangChain Integration

Convert MCP tools to LangChain `StructuredTool` objects for use with LangChain agents:

```python
from sap_cloud_sdk.agentgateway import create_client
from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain

agw_client = create_client(tenant_subdomain="my-tenant")
tools = await agw_client.list_mcp_tools()

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

## Concepts

### Agent Types

- **LoB (Line of Business) Agent**: Uses BTP Destination Service for credentials. Requires `tenant_subdomain`. Tools are auto-discovered from destination fragments.
- **Customer Agent**: Uses file-based credentials mounted on the pod filesystem with mTLS authentication. MCP servers are defined in the credentials file's `integrationDependencies`.

The SDK automatically detects the agent type based on the presence of a credentials file.


## API

### Factory Function

```python
def create_client(
    tenant_subdomain: str | Callable[[], str] | None = None,
) -> AgentGatewayClient
```

- `tenant_subdomain`: Required for LoB agents, ignored for Customer agents. Can be a string or callable.

### AgentGatewayClient

```python
class AgentGatewayClient:
    async def list_mcp_tools(
        self,
        app_tid: str | None = None,
    ) -> list[MCPTool]

    async def call_mcp_tool(
        self,
        tool: MCPTool,
        user_token: str | Callable[[], str] | None = None,
        app_tid: str | None = None,
        **kwargs,
    ) -> str
```


