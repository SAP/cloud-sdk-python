"""Data models for Agent Gateway MCP tools."""

from dataclasses import dataclass
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
    """Credentials for customer agent mTLS authentication.

    Loaded from the credentials file mounted on the pod filesystem.
    Used internally by the customer agent flow.

    Attributes:
        token_service_url: IAS token service endpoint URL
        client_id: IAS client ID
        certificate: PEM-encoded client certificate
        private_key: PEM-encoded private key
        gateway_url: Agent Gateway base URL
        integration_dependencies: List of MCP servers with their ord_id and global_tenant_id.
    """

    token_service_url: str
    client_id: str
    certificate: str
    private_key: str
    gateway_url: str
    integration_dependencies: list[IntegrationDependency]
