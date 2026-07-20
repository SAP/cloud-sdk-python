"""Data models for Agent Gateway MCP tools."""

from dataclasses import dataclass, field
from typing import Any


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
