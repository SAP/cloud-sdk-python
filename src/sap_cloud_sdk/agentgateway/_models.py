"""Data models for Agent Gateway MCP tools."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sap_cloud_sdk.agentgateway.config import (
    DEFAULT_MAX_MCP_TOOLS_CACHE_SIZE,
    DEFAULT_MCP_TOOLS_CACHE_TTL_SECONDS,
)

if TYPE_CHECKING:
    from sap_cloud_sdk.agentgateway._tools_cache import MCPToolsCache


@dataclass
class AuthResult:
    """Authentication result from Agent Gateway.

    Contains the access token and the Agent Gateway URL.

    Attributes:
        access_token: Raw JWT access token (no "Bearer " prefix).
        gateway_url: Agent Gateway base URL (no trailing slash).

    Example:
        ```python
        from sap_cloud_sdk.agentgateway import create_client

        agw_client = create_client(tenant_subdomain="my-tenant")

        auth = await agw_client.get_system_auth()
        print(auth.access_token)  # raw JWT
        print(auth.gateway_url)   # "https://agw.example.com"
        ```
    """

    access_token: str
    gateway_url: str


@dataclass
class MCPTool:
    """MCP tool discovered from Agent Gateway.

    Represents a tool available on an MCP server registered via BTP Destination
    Service fragments. Tools are discovered using list_mcp_tools() and invoked
    using call_mcp_tool().

    Attributes:
        name: Tool name on MCP server (used when calling the tool)
        server_name: MCP server name from serverInfo.name
        description: Tool description
        input_schema: JSON schema for tool input parameters
        url: MCP endpoint URL
        fragment_name: Destination fragment name (used for auth lookup)
    """

    name: str
    server_name: str
    description: str
    input_schema: dict[str, Any]
    url: str
    fragment_name: str | None = None


@dataclass
class IntegrationDependency:
    """MCP server mapping from credentials integrationDependencies.

    Maps an ORD ID to its corresponding Global Tenant ID.

    Attributes:
        ord_id: Open Resource Discovery ID of the MCP server
        global_tenant_id: Global Tenant ID for URL construction
    """

    ord_id: str
    global_tenant_id: str


@dataclass
class CustomerCredentials:
    """Credentials for customer agent authentication.

    Loaded from the credentials file mounted on the pod filesystem (STANDARD mode)
    or from environment variables (TRANSPARENT mode).
    Used internally by the customer agent flow.

    Attributes:
        token_service_url: IAS token service endpoint URL
        client_id: IAS client ID
        certificate: PEM-encoded client certificate (required for STANDARD mode, None for TRANSPARENT)
        private_key: PEM-encoded private key (required for STANDARD mode, None for TRANSPARENT)
        gateway_url: Agent Gateway base URL
        integration_dependencies: List of MCP servers with their ord_id and global_tenant_id.
        tls_mode: TLS authentication mode (STANDARD or TRANSPARENT)
    """

    token_service_url: str
    client_id: str
    gateway_url: str
    integration_dependencies: list[IntegrationDependency]
    certificate: str | None = None
    private_key: str | None = None


@dataclass
class JsonRpcError:
    """Parsed JSON-RPC error from an Agent Gateway response.

    AGW returns HTTP 200 with a JSON-RPC error body when the request is
    structurally valid but the server encountered an error.

    Example: {"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal Server Error"}}

    Attributes:
        code: JSON-RPC error code.
        message: Human-readable error message from AGW.
    """

    code: int
    message: str

    @classmethod
    def parse(cls, text: str) -> "JsonRpcError | None":
        try:
            data = json.loads(text)
            error = data.get("error", {})
            return cls(code=error["code"], message=error["message"])
        except Exception:
            return None


@dataclass
class AgentCard:
    """Agent Card as returned by the A2A well-known endpoint.

    Contains the raw payload from /.well-known/agent-card.json, plus
    the ORD ID and global tenant ID of the agent.

    Attributes:
        raw: Full parsed JSON payload from the agent card endpoint.
    """

    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Agent:
    """A2A agent discovered via Agent Gateway fragment listing.

    Attributes:
        ord_id: Open Resource Discovery ID of the agent.
        agent_card: Agent Card fetched from the A2A well-known endpoint.
    """

    ord_id: str
    agent_card: AgentCard


@dataclass
class AgentCardFilter:
    """Filter options for list_agent_cards.

    All fields are optional. When multiple fields are set they are applied
    together (AND semantics). Empty lists are treated the same as None (no
    filtering on that field).

    Attributes:
        agent_names: Agent card names to include (matched against the `name`
            field in the agent card JSON). Applied after fetching all cards.
        ord_ids: ORD IDs to include (extracted from the fragment URL).
            Applied before fetching, skipping non-matching fragments.

    Example:
        ```python
        from sap_cloud_sdk.agentgateway import AgentCardFilter

        agents = await agw_client.list_agent_cards(
            filter=AgentCardFilter(
                agent_names=["Sample Agent"],
                ord_ids=["sap.s4:apiAccess:agent:v1"],
            )
        )
        ```
    """

    agent_names: list[str] = field(default_factory=list)
    ord_ids: list[str] = field(default_factory=list)


@dataclass
class MCPToolFilter:
    """Filter options for list_mcp_tools.

    All fields are optional. When multiple fields are set they are applied
    together (AND semantics). Empty lists are treated the same as None (no
    filtering on that field).

    Attributes:
        names: Tool names to include (matched against MCPTool.name).
            Applied after fetching.
        ord_ids: ORD IDs to include (extracted from the fragment URL for LoB
            agents, or matched against IntegrationDependency.ord_id for
            customer agents). Applied before fetching, skipping non-matching
            fragments.

    Example:
        ```python
        from sap_cloud_sdk.agentgateway import MCPToolFilter

        tools = await agw_client.list_mcp_tools(
            filter=MCPToolFilter(
                names=["get-sales-order"],
                ord_ids=["sap.s4:apiAccess:salesOrder:v1"],
            )
        )
        ```
    """

    names: list[str] = field(default_factory=list)
    ord_ids: list[str] = field(default_factory=list)


class CacheOptions:
    """Options for caching the result of list_mcp_tools.

    Pass an instance to list_mcp_tools(cache=...) to enable result caching.
    The same instance can be reused across calls — cache state is stored on
    it. Call evict() to force a fresh fetch on the next call.

    Args:
        ttl: Cache lifetime in seconds. Defaults to 600 s.
        max_size: Maximum number of distinct cached entries (keyed by filter
            combo + auth type). Oldest entry is evicted when the limit is
            exceeded. Defaults to 32.

    Example:
        ```python
        from sap_cloud_sdk.agentgateway import CacheOptions

        cache = CacheOptions(ttl=300)
        tools = await agw_client.list_mcp_tools(cache=cache)

        # Later — force a fresh fetch (e.g. after a tool was added):
        cache.evict()
        tools = await agw_client.list_mcp_tools(cache=cache)
        ```

    Note:
        Cache is in-process only. It is not shared across client instances,
        processes, or Kubernetes pods. Two concurrent calls that both miss
        the cache will both fetch independently — the last writer wins, no
        data corruption occurs.
    """

    def __init__(
        self,
        ttl: float = DEFAULT_MCP_TOOLS_CACHE_TTL_SECONDS,
        max_size: int = DEFAULT_MAX_MCP_TOOLS_CACHE_SIZE,
    ) -> None:
        self.ttl = ttl
        self.max_size = max_size
        self._cache: MCPToolsCache | None = None

    def evict(self) -> None:
        """Clear all cached tool list entries. Forces a fresh fetch on the next call."""
        if self._cache is not None:
            self._cache.evict()
