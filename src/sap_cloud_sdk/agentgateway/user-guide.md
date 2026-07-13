# Agent Gateway User Guide

This module provides a framework-agnostic client for discovering and invoking MCP tools and A2A agent cards via SAP Agent Gateway. It automatically detects the agent type (LoB vs Customer) based on credential file presence and handles authentication accordingly.

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
    print(f"{tool.name}: {tool.description}")

# Discover tools with user principal propagation
tools = await agw_client.list_mcp_tools(user_token="user-jwt")

# Invoke a tool with user principal propagation
result = await agw_client.call_mcp_tool(
    tool=tools[0],
    user_token="user-jwt",
    cost_center="1000",
)
```

### LoB Agent Flow

LoB agents use BTP Destination Service for credential management. Tools and A2A agents are auto-discovered from destination fragments.

```python
from sap_cloud_sdk.agentgateway import ClientConfig, create_client

config = ClientConfig(timeout=30.0)
agw_client = create_client(tenant_subdomain="my-tenant", config=config)

# Discover MCP tools (auto-discovered from destination fragments)
# Pass user_token to use principal propagation when listing tools
tools = await agw_client.list_mcp_tools(user_token="user-jwt")

# Invoke a tool (user_token required for principal propagation)
result = await agw_client.call_mcp_tool(
    tool=tools[0],
    user_token="user-jwt",
    order_id="12345",
)
```

### A2A Agent Cards (LoB only)

Discover A2A agents and their agent cards from destination fragments labelled `agw.a2a.server`. Each fragment must have a `URL` property; the agent card is fetched from `{URL}/.well-known/agent-card.json` and the ORD ID is extracted from the second-to-last URL path segment.

```python
from sap_cloud_sdk.agentgateway import AgentCardFilter, create_client

agw_client = create_client(tenant_subdomain="my-tenant")

# Discover all A2A agents
agents = await agw_client.list_agent_cards()

for agent in agents:
    print(agent.ord_id)
    print(agent.agent_card.raw)  # full agent card JSON payload

# Filter by agent card name (post-fetch) or ORD ID (pre-fetch)
agents = await agw_client.list_agent_cards(
    filter=AgentCardFilter(
        agent_names=["Sample Agent"],
        ord_ids=["sap.s4:apiAccess:purchaseOrderAI:agent:v1"],
    )
)
```

### LangChain Integration

Convert MCP tools to LangChain `StructuredTool` objects for use with LangChain agents:

```python
from sap_cloud_sdk.agentgateway import create_client
from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain

agw_client = create_client(tenant_subdomain="my-tenant")
tools = await agw_client.list_mcp_tools(user_token="user-jwt")

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

By default, optional tool parameters that resolve to `None` are not forwarded to `call_mcp_tool`. Set `omit_none=False` to forward them explicitly:

```python
mcp_tool_to_langchain(
    t,
    agw_client.call_mcp_tool,
    get_user_token=lambda: request.headers["Authorization"],
    omit_none=False,
)
```

The converter maps each property's JSON Schema `"type"` to the corresponding Python type so Pydantic validates and forwards the correct native type to the MCP server:

| JSON Schema type | Python type |
|------------------|-------------|
| `"string"`       | `str`       |
| `"integer"`      | `int`       |
| `"number"`       | `float`     |
| `"boolean"`      | `bool`      |
| `"array"`        | `list`      |
| `"object"`       | `dict`      |
| missing / other  | `Any`       |

Optional fields (not listed in `"required"`) are typed as `T | None` with a `None` default.

## Concepts

### Agent Types

- **LoB (Line of Business) Agent**: Uses BTP Destination Service for credentials. Requires `tenant_subdomain`. MCP tools and A2A agent cards are auto-discovered from destination fragments.
- **Customer Agent**: Uses file-based credentials mounted on the pod filesystem with mTLS authentication. MCP servers are defined in the credentials file's `integrationDependencies`. A2A agent card discovery is not yet supported.

The SDK automatically detects the agent type based on the presence of a credentials file.

### Fragments and Labels

The SDK discovers resources via BTP Destination Service fragments filtered by the `sap-managed-runtime-type` label:

| Label value | Resource |
|---|---|
| `agw.mcp.server` | MCP tool server — `URL` property points to the MCP endpoint |
| `agw.a2a.server` | A2A agent — `URL` property is the agent base URL; ORD ID is extracted from the second-to-last URL path segment |
| `subscriber.ias` | IAS credential fragment for system-scoped token acquisition |
| `subscriber.ias.user` | IAS credential fragment for user-scoped token exchange |

## API

### Factory Function

```python
def create_client(
    tenant_subdomain: str | Callable[[], str] | None = None,
    config: ClientConfig | None = None,
) -> AgentGatewayClient
```

- `tenant_subdomain`: Required for LoB agents, ignored for Customer agents. Can be a string or callable.
- `config`: Optional `ClientConfig` used to control HTTP timeout and in-memory token cache behavior.

### ClientConfig

Use `ClientConfig` to tune request timeouts and token cache behavior for a client instance.

```python
from sap_cloud_sdk.agentgateway import ClientConfig, create_client

config = ClientConfig(
    timeout=30.0,
    fallback_token_ttl_seconds=300.0,
    token_expiry_buffer_seconds=30.0,
    max_system_token_cache_size=32,
    max_user_token_cache_size=256,
)

agw_client = create_client(tenant_subdomain="my-tenant", config=config)
```

- `timeout`: HTTP timeout in seconds for token requests, MCP calls, and agent card fetches. Default: `60.0`.
- `fallback_token_ttl_seconds`: Used when the token response does not include expiry metadata. Default: `300.0`.
- `token_expiry_buffer_seconds`: Safety buffer subtracted from explicit token expiries before a cached token is reused. Default: `30.0`.
- `max_system_token_cache_size`: Maximum number of cached system tokens per client instance. Default: `32`.
- `max_user_token_cache_size`: Maximum number of cached exchanged user tokens per client instance. Default: `256`.

The SDK keeps token caches per `AgentGatewayClient` instance and reuses valid cached tokens for repeated authentication calls. System and user token caches are bounded independently with least-recently-used eviction.

### AgentGatewayClient

```python
class AgentGatewayClient:
    async def list_mcp_tools(
        self,
        user_token: str | Callable[[], str] | None = None,
        app_tid: str | None = None,
    ) -> list[MCPTool]

    async def call_mcp_tool(
        self,
        tool: MCPTool,
        user_token: str | Callable[[], str] | None = None,
        app_tid: str | None = None,
        **kwargs,
    ) -> str

    async def list_agent_cards(
        self,
        filter: AgentCardFilter | None = None,
    ) -> list[Agent]

    def get_ias_client_id(self) -> str
```

#### `get_ias_client_id()`

Returns the IAS client ID. Automatically detects agent type:

- **Customer agents**: reads `client_id` directly from the mounted credentials file.
- **LoB agents**: fetches the IAS destination (`sap-managed-runtime-ias-{landscape}`) at provider subaccount level and returns the `clientId` destination property.

Raises `AgentGatewaySDKError` if the value cannot be resolved.

```python
agw_client = create_client(tenant_subdomain="my-tenant")
client_id = agw_client.get_ias_client_id()
```

### AgentCardFilter

```python
from sap_cloud_sdk.agentgateway import AgentCardFilter

AgentCardFilter(
    agent_names=[],  # agent card names to include (matched against card JSON `name`); empty = no filter
    ord_ids=[],      # ORD IDs to include (extracted from fragment URL); empty = no filter
)
```

Both fields default to empty lists. Filters are applied with AND semantics: if both are set, an agent must match both to be included. `agent_names` is applied after fetching (requires reading the card); `ord_ids` is applied before fetching (extracted from the fragment URL, no card request needed).

### Data Models

```python
@dataclass
class Agent:
    ord_id: str       # ORD ID from fragment ordId property
    agent_card: AgentCard

@dataclass
class AgentCard:
    raw: dict         # full parsed JSON from /.well-known/agent-card.json

@dataclass
class MCPTool:
    name: str
    server_name: str
    description: str
    input_schema: dict
    url: str
    fragment_name: str | None
```
