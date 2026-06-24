# Agent Gateway User Guide

This module provides a framework-agnostic client for discovering and invoking MCP tools via SAP Agent Gateway. It automatically detects the agent type (LoB vs Customer) based on credential file presence and handles authentication accordingly.

## Installation

This package is part of the SAP Cloud SDK for Python. Import and use it directly in your application.

For LangChain integration, install the optional extra:

```bash
pip install sap-cloud-sdk[langchain]
```

## Quick Start

### Customer Agent Flow — Standard Mode (file-based mTLS)

Customer agents use file-based credentials with mTLS authentication. The SDK reads the credentials file from the path in `AGW_CREDENTIALS_PATH`, or falls back to the default Kyma mount path `/etc/ums/credentials/credentials`. MCP servers are read from `integrationDependencies` in the credentials file.

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

### Customer Agent Flow — Transparent Mode (gateway-injected mTLS)

In transparent mode the OpenShell Gateway intercepts HTTPS connections and injects the mTLS client certificate at the TLS layer. The agent never loads certificate or private key material — only the service endpoint URLs need to be visible to the agent process.

Set `AGW_TLS_MODE=transparent` and provide the required environment variables:

```bash
export AGW_TLS_MODE="transparent"
export CLIENT_ID="sb-abc123|xsuaa_std!b318"
export TOKEN_SERVICE_URL="https://your-tenant.accounts.ondemand.com/oauth2/token"
export GATEWAY_URL="https://agent-gateway.example.com"
export INTEGRATION_DEPENDENCIES='[{"ordId": "sap.app:apiResource:my-tool:v1", "globalTenantId": "123456"}]'
export HTTPS_PROXY="https://openshell-gateway:3128"  # set automatically by OpenShell
```

```python
from sap_cloud_sdk.agentgateway import create_client
from sap_cloud_sdk.agentgateway.config import ClientConfig

# Option 1: read AGW_TLS_MODE from environment
client = create_client(config=ClientConfig.from_env())

# Option 2: set explicitly in code
from sap_cloud_sdk.agentgateway.config import TlsMode
client = create_client(config=ClientConfig(tls_mode=TlsMode.TRANSPARENT))

# Usage is identical to standard mode
tools = await client.list_mcp_tools()
result = await client.call_mcp_tool(tool=tools[0], user_token="user-jwt", cost_center="1000")
```

**When to use transparent mode:**

- The agent runs inside an OpenShell Gateway sandbox with a `PolicyClass` configured for `tls: terminate` and `credentialRewrite: requestBody: true` on the IAS endpoint.
- You want to eliminate TLS certificates and private keys from the agent process memory and filesystem entirely.
- Credential rotation without pod restarts is required (secrets are updated in the gateway, not the agent).

**Credential visibility comparison:**

| Credential | Standard mode | Transparent mode |
|---|---|---|
| `CLIENT_ID` | In credentials file | In env var (gateway resolves placeholder) |
| `CERTIFICATE` | In credentials file + SSLContext | Never in agent — gateway-injected |
| `PRIVATE_KEY` | In credentials file + SSLContext | Never in agent — gateway-injected |
| `TOKEN_SERVICE_URL` | In credentials file | In env var |
| `GATEWAY_URL` | In credentials file | In env var |

### LoB Agent Flow

LoB agents use BTP Destination Service for credential management. Tools are auto-discovered from destination fragments.

```python
from sap_cloud_sdk.agentgateway import ClientConfig, create_client

config = ClientConfig(timeout=30.0)
agw_client = create_client(tenant_subdomain="my-tenant", config=config)

# Discover tools (auto-discovered from destination fragments)
# Pass user_token to use principal propagation when listing tools
tools = await agw_client.list_mcp_tools(user_token="user-jwt")

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

## Concepts

### Agent Types

- **LoB (Line of Business) Agent**: Uses BTP Destination Service for credentials. Requires `tenant_subdomain`. Tools are auto-discovered from destination fragments.
- **Customer Agent**: Uses credentials for mTLS authentication against IAS. MCP servers are defined in `integrationDependencies`. Supports two sub-modes:
  - **Standard mode** (default): credentials are read from a file mounted on the pod filesystem. The agent loads the certificate and private key into an `ssl.SSLContext` and performs the mTLS handshake directly.
  - **Transparent mode** (`AGW_TLS_MODE=transparent`): the OpenShell Gateway intercepts HTTPS connections and injects the client certificate at the TLS layer. The agent reads only endpoint URLs from environment variables and never accesses certificate or private key material.

The SDK automatically selects the agent type and TLS mode based on credential file presence and the `AGW_TLS_MODE` environment variable.


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

Use `ClientConfig` to tune request timeouts, token cache behaviour, and TLS mode for a client instance.

```python
from sap_cloud_sdk.agentgateway import ClientConfig, create_client
from sap_cloud_sdk.agentgateway.config import TlsMode

config = ClientConfig(
    timeout=30.0,
    fallback_token_ttl_seconds=300.0,
    token_expiry_buffer_seconds=30.0,
    max_system_token_cache_size=32,
    max_user_token_cache_size=256,
    tls_mode=TlsMode.STANDARD,  # or TlsMode.TRANSPARENT
)

agw_client = create_client(tenant_subdomain="my-tenant", config=config)
```

Use `ClientConfig.from_env()` to resolve `tls_mode` automatically from the `AGW_TLS_MODE` environment variable:

```python
config = ClientConfig.from_env()  # reads AGW_TLS_MODE; defaults to STANDARD
agw_client = create_client(config=config)
```

- `timeout`: HTTP timeout in seconds for token requests and MCP calls. Default: `60.0`.
- `fallback_token_ttl_seconds`: Used when the token response does not include expiry metadata. Default: `300.0`.
- `token_expiry_buffer_seconds`: Safety buffer subtracted from explicit token expiries before a cached token is reused. Default: `30.0`.
- `max_system_token_cache_size`: Maximum number of cached system tokens per client instance. Default: `32`.
- `max_user_token_cache_size`: Maximum number of cached exchanged user tokens per client instance. Default: `256`.
- `tls_mode`: `TlsMode.STANDARD` (default) or `TlsMode.TRANSPARENT`. Controls whether the agent performs mTLS directly or delegates it to the OpenShell Gateway. See [Transparent Mode](#customer-agent-flow--transparent-mode-gateway-injected-mtls) above.

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
```
