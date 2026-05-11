"""Data models for Agent Gateway MCP tools."""

import hashlib
import re
from dataclasses import dataclass
from typing import Any


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

    @property
    def namespaced_name(self) -> str:
        """Unique tool name safe for LLM APIs: sanitized, namespaced, max 64 chars.

        LLM tool-calling APIs (Anthropic, OpenAI) require names matching
        ^[a-zA-Z0-9-_]+$ with a max length of 64 characters.

        This property combines server_name and tool name to avoid collisions
        across multiple MCP servers, then sanitizes and enforces the limit.

        Examples:
            Short names pass through unchanged:
                "myserver__list_orders" (21 chars) → "myserver__list_orders"

            Invalid chars are replaced with underscores:
                "my.server:v1__get/data" → "my_server_v1__get_data"

            Names over 64 chars are truncated with a hash suffix for uniqueness:
                "sales_order_mcp_demo__get_supplier_operational_eval_scores_by_region" (70 chars)
                → "sales_order_mcp_demo__get_supplier_operational_eval_s_a3b7c9d1" (64 chars)

            Two servers with the same tool name remain distinct:
                "server_a__get_metadata" vs "server_b__get_metadata"
        """
        raw = f"{self.server_name}__{self.name}"
        sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "_", raw)
        if len(sanitized) <= 64:
            return sanitized
        suffix = hashlib.sha256(sanitized.encode()).hexdigest()[:8]
        return f"{sanitized[:55]}_{suffix}"


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
