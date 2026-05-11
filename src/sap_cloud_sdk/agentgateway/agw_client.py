"""Agent Gateway client implementation.

Framework-agnostic discovery and execution of MCP tools. Automatically
detects agent type (LoB vs Customer) based on credential file presence.

- LoB agents: Use BTP Destination Service for credentials
- Customer agents: Use file-based credentials mounted on pod with mTLS auth
"""

import logging
from typing import Callable

from sap_cloud_sdk.agentgateway._models import MCPTool
from sap_cloud_sdk.agentgateway._customer import (
    detect_customer_agent_credentials,
    load_customer_credentials,
    get_mcp_tools_customer,
    call_mcp_tool_customer,
)
from sap_cloud_sdk.agentgateway._lob import get_mcp_tools_lob, call_mcp_tool_lob
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics

logger = logging.getLogger(__name__)


class AgentGatewayClient:
    """Client for discovering and invoking MCP tools via SAP Agent Gateway.

    Automatically detects agent type (LoB vs Customer) based on the
    presence of credential files.

    - LoB agents: Requires tenant_subdomain, uses BTP Destination Service
    - Customer agents: Uses file-based credentials with mTLS authentication.
      MCP servers are read from integrationDependencies in the credentials file.

    Example (LoB agent):
        ```python
        from sap_cloud_sdk.agentgateway import create_client

        agw_client = create_client(tenant_subdomain="my-tenant")

        # Discover tools
        tools = await agw_client.list_mcp_tools()

        # Invoke a tool
        result = await agw_client.call_mcp_tool(
            tool=tools[0],
            user_token="user-jwt",
            order_id="12345",
        )
        ```

    Example (Customer agent):
        ```python
        from sap_cloud_sdk.agentgateway import create_client

        agw_client = create_client()

        # Discover tools (reads all servers from credentials integrationDependencies)
        tools = await agw_client.list_mcp_tools()

        # Invoke a tool
        result = await agw_client.call_mcp_tool(
            tool=tools[0],
            user_token="user-jwt",
            cost_center="1000",
        )
        ```
    """

    def __init__(
        self,
        tenant_subdomain: str | Callable[[], str] | None = None,
    ):
        """Initialize the Agent Gateway client.

        Args:
            tenant_subdomain: Tenant subdomain for multi-tenant lookup.
                Can be a string or a callable returning a string.
                Required for LoB agents, ignored for Customer agents.
        """
        self._tenant_subdomain = tenant_subdomain

    @staticmethod
    def _resolve_value(
        value: str | Callable[[], str] | None,
        error_message: str,
    ) -> str:
        """Resolve a value from string or callable.

        Args:
            value: String, callable returning string, or None.
            error_message: Error message if value is empty.

        Returns:
            Resolved string value.

        Raises:
            AgentGatewaySDKError: If resolved value is empty.
        """
        resolved = value() if not isinstance(value, str) and callable(value) else value

        if not resolved or not resolved.strip():
            raise AgentGatewaySDKError(error_message)

        return resolved

    def _resolve_tenant_subdomain(self) -> str:
        """Resolve tenant subdomain from string or callable."""
        return self._resolve_value(
            self._tenant_subdomain,
            "tenant_subdomain is required for LoB agent flow.",
        )

    @record_metrics(Module.AGENTGATEWAY, Operation.AGENTGATEWAY_LIST_MCP_TOOLS)
    async def list_mcp_tools(
        self,
        app_tid: str | None = None,
    ) -> list[MCPTool]:
        """List all MCP tools from MCP servers.

        Automatically detects agent type (LoB vs Customer) based on
        credential file presence.

        For LoB agents: Uses Phase 1 auth (client-scoped) via BTP Destination Service.
            Tools are auto-discovered from destination fragments.
        For Customer agents: Uses mTLS client credentials.
            Tools are discovered from all servers in credentials integrationDependencies.

        Args:
            app_tid: BTP Application Tenant ID of the subscriber.
                Only used for customer agents.

        Returns:
            List of MCPTool objects from all MCP servers.

        Raises:
            AgentGatewaySDKError: If credential loading or token acquisition fails.

        Example:
            ```python
            tools = await agw_client.list_mcp_tools()
            for tool in tools:
                print(f"{tool.namespaced_name}: {tool.description}")
            ```
        """
        try:
            # Check for customer agent credentials
            credentials_path = detect_customer_agent_credentials()
            if credentials_path:
                logger.info(
                    "Customer agent credentials detected at '%s'", credentials_path
                )
                credentials = load_customer_credentials(credentials_path)
                return await get_mcp_tools_customer(credentials, app_tid)

            # LoB flow - requires tenant_subdomain
            if app_tid:
                logger.warning("app_tid parameter ignored for LoB agent flow")

            tenant = self._resolve_tenant_subdomain()
            return await get_mcp_tools_lob(tenant)

        except AgentGatewaySDKError:
            # Re-raise SDK errors as-is
            raise
        except Exception as e:
            logger.exception("Unexpected error during tool discovery")
            raise AgentGatewaySDKError(f"Tool discovery failed: {e}") from e

    @record_metrics(Module.AGENTGATEWAY, Operation.AGENTGATEWAY_CALL_MCP_TOOL)
    async def call_mcp_tool(
        self,
        tool: MCPTool,
        user_token: str | Callable[[], str] | None = None,
        app_tid: str | None = None,
        **kwargs,
    ) -> str:
        """Invoke an MCP tool.

        Automatically detects agent type (LoB vs Customer) based on
        credential file presence.

        For LoB agents: Uses Phase 2 auth (user-scoped) via BTP Destination Service
            token exchange. Principal propagation ensures LoB systems see user identity.
        For Customer agents: Uses mTLS + jwt-bearer grant to exchange user token
            for AGW-scoped token with user identity preserved. If user_token is not
            provided, falls back to system token (no principal propagation).

        Args:
            tool: MCPTool object (from list_mcp_tools).
            user_token: User's JWT for principal propagation.
                Can be a string or a callable returning a string.
                Required for LoB agents.
                Optional for Customer agents (falls back to system token if not provided).
            app_tid: BTP Application Tenant ID of the subscriber.
                Only used for customer agents. This is passed to the token service
                for tenant-scoped token exchange.
                TODO: This parameter's requirement is still being clarified with
                the IBD team and may be removed if unnecessary.
            **kwargs: Tool input parameters (passed directly to the tool).

        Returns:
            Tool execution result as string.

        Raises:
            AgentGatewaySDKError: If user_token or tenant_subdomain is required
                but not provided (LoB flow), or if token exchange/tool invocation fails.

        Example:
            ```python
            # Note: kwargs are tool-specific input parameters.
            # Check tool.input_schema for expected parameters.
            result = await agw_client.call_mcp_tool(
                tool=tools[0],
                user_token="user-jwt",
                order_id="12345",  # example tool-specific parameter
            )
            ```
        """
        try:
            # Check for customer agent credentials
            credentials_path = detect_customer_agent_credentials()
            if credentials_path:
                logger.info(
                    "Customer agent credentials detected at '%s'", credentials_path
                )

                # Resolve user_token if provided (optional for customer flow)
                resolved_user_token = None
                if user_token:
                    resolved_user_token = (
                        user_token()
                        if not isinstance(user_token, str) and callable(user_token)
                        else user_token
                    )
                    if resolved_user_token:
                        resolved_user_token = resolved_user_token.strip() or None

                credentials = load_customer_credentials(credentials_path)
                return await call_mcp_tool_customer(
                    credentials, tool, resolved_user_token, app_tid, **kwargs
                )

            # LoB flow - requires user_token and tenant_subdomain
            resolved_user_token = self._resolve_value(
                user_token,
                "user_token is required for LoB agent tool invocation.",
            )

            if app_tid:
                logger.warning("app_tid parameter ignored for LoB agent flow")

            tenant = self._resolve_tenant_subdomain()
            return await call_mcp_tool_lob(tool, resolved_user_token, tenant, **kwargs)

        except AgentGatewaySDKError:
            # Re-raise SDK errors as-is
            raise
        except Exception as e:
            logger.exception("Unexpected error during tool invocation")
            raise AgentGatewaySDKError(
                f"Tool invocation failed for '{tool.name}': {e}"
            ) from e


def create_client(
    tenant_subdomain: str | Callable[[], str] | None = None,
) -> AgentGatewayClient:
    """Create an Agent Gateway client for discovering and invoking MCP tools.

    Automatically detects agent type (LoB vs Customer) based on
    credential file presence.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
            Can be a string or a callable returning a string.
            Required for LoB agents, ignored for Customer agents.

    Returns:
        AgentGatewayClient instance.

    Example (LoB agent):
        ```python
        from sap_cloud_sdk.agentgateway import create_client

        agw_client = create_client(tenant_subdomain="my-tenant")

        # Discover tools
        tools = await agw_client.list_mcp_tools()

        # Invoke a tool
        # Note: kwargs are tool-specific input parameters.
        # Check tool.input_schema for expected parameters.
        result = await agw_client.call_mcp_tool(
            tool=tools[0],
            user_token="user-jwt",
            order_id="12345",  # example tool-specific parameter
        )
        ```

    Example (Customer agent):
        ```python
        from sap_cloud_sdk.agentgateway import create_client

        agw_client = create_client()

        # Discover tools (reads all servers from credentials integrationDependencies)
        tools = await agw_client.list_mcp_tools()

        # Invoke a tool
        # Note: kwargs are tool-specific input parameters.
        # Check tool.input_schema for expected parameters.
        result = await agw_client.call_mcp_tool(
            tool=tools[0],
            user_token="user-jwt",
            cost_center="1000",  # example tool-specific parameter
        )
        ```
    """
    return AgentGatewayClient(tenant_subdomain=tenant_subdomain)
