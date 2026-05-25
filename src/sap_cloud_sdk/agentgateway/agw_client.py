"""Agent Gateway client implementation.

Framework-agnostic discovery and execution of MCP tools. Automatically
detects agent type (LoB vs Customer) based on credential file presence.

- LoB agents: Use BTP Destination Service for credentials
- Customer agents: Use file-based credentials mounted on pod with mTLS auth
"""

import asyncio
import logging
from typing import Callable

from sap_cloud_sdk.agentgateway.config import ClientConfig
from sap_cloud_sdk.agentgateway._customer import (
    call_mcp_tool_customer,
    detect_customer_agent_credentials,
    exchange_user_token,
    get_mcp_tools_customer,
    get_system_token_mtls,
    load_customer_credentials,
)
from sap_cloud_sdk.agentgateway._lob import (
    call_mcp_tool_lob,
    fetch_system_auth,
    fetch_user_auth,
    get_mcp_tools_lob,
)
from sap_cloud_sdk.agentgateway._models import AuthResult, MCPTool
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

    Example (auth for external use):
        ```python
        from sap_cloud_sdk.agentgateway import create_client

        agw_client = create_client(tenant_subdomain="my-tenant")

        # Get system-scoped auth (token + gateway URL)
        auth = await agw_client.get_system_auth()
        print(auth.access_token)  # raw JWT
        print(auth.gateway_url)   # "https://agw.example.com"

        # Get user-scoped auth (token exchange + gateway URL)
        auth = await agw_client.get_user_auth(user_token="user-jwt")
        print(auth.access_token)  # exchanged JWT with user identity
        print(auth.gateway_url)   # "https://agw.example.com"
        ```
    """

    def __init__(
        self,
        tenant_subdomain: str | Callable[[], str] | None = None,
        config: ClientConfig | None = None,
    ):
        """Initialize the Agent Gateway client.

        Args:
            tenant_subdomain: Tenant subdomain for multi-tenant lookup.
                Can be a string or a callable returning a string.
                Required for LoB agents, ignored for Customer agents.
            config: Client configuration. Uses defaults if not provided.
        """
        self._tenant_subdomain = tenant_subdomain
        self._config = config or ClientConfig()

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

    @record_metrics(Module.AGENTGATEWAY, Operation.AGENTGATEWAY_GET_SYSTEM_AUTH)
    async def get_system_auth(self, app_tid: str | None = None) -> AuthResult:
        """Get system-scoped authentication (client_credentials flow).

        Automatically detects agent type (LoB vs Customer) based on
        credential file presence.

        Args:
            app_tid: BTP Application Tenant ID of the subscriber.
                Only used for customer agents. This is passed to the token
                service for tenant-scoped token requests.

        Returns:
            AuthResult with raw access token (JWT) and Agent Gateway URL.

        Raises:
            AgentGatewaySDKError: If tenant_subdomain is required but not
                provided (LoB), or if token acquisition fails.

        Example:
            ```python
            auth = await agw_client.get_system_auth()
            headers = {"Authorization": f"Bearer {auth.access_token}"}
            # auth.gateway_url is the Agent Gateway base URL
            ```
        """
        try:
            credentials_path = detect_customer_agent_credentials()
            if credentials_path:
                logger.info(
                    "Customer agent credentials detected at '%s'", credentials_path
                )
                credentials = load_customer_credentials(credentials_path)
                loop = asyncio.get_running_loop()
                token = await loop.run_in_executor(
                    None,
                    get_system_token_mtls,
                    credentials,
                    self._config.timeout,
                    app_tid,
                )
                return AuthResult(
                    access_token=token,
                    gateway_url=credentials.gateway_url,
                )

            # LoB flow
            if app_tid:
                logger.warning("app_tid parameter ignored for LoB agent flow")

            tenant = self._resolve_tenant_subdomain()
            token, gateway_url = await fetch_system_auth(tenant)
            return AuthResult(access_token=token, gateway_url=gateway_url)

        except AgentGatewaySDKError:
            raise
        except Exception as e:
            logger.exception("Unexpected error during system auth acquisition")
            raise AgentGatewaySDKError(f"System auth acquisition failed: {e}") from e

    @record_metrics(Module.AGENTGATEWAY, Operation.AGENTGATEWAY_GET_USER_AUTH)
    async def get_user_auth(
        self,
        user_token: str | Callable[[], str] | None,
        app_tid: str | None = None,
    ) -> AuthResult:
        """Exchange a user token for AGW-scoped authentication (token exchange).

        Automatically detects agent type (LoB vs Customer) based on
        credential file presence.

        Args:
            user_token: User's JWT for principal propagation.
                Can be a string or a callable returning a string.
            app_tid: BTP Application Tenant ID of the subscriber.
                Only used for customer agents. This is passed to the token
                service for tenant-scoped token exchange.

        Returns:
            AuthResult with raw access token (JWT, user identity embedded)
            and Agent Gateway URL.

        Raises:
            AgentGatewaySDKError: If user_token is empty, or tenant_subdomain
                is required but not provided (LoB), or if token exchange fails.

        Example:
            ```python
            auth = await agw_client.get_user_auth(user_token="user-jwt")
            headers = {"Authorization": f"Bearer {auth.access_token}"}
            # auth.gateway_url is the Agent Gateway base URL
            ```
        """
        try:
            resolved_user_token = self._resolve_value(
                user_token,
                "user_token is required for token exchange.",
            )

            credentials_path = detect_customer_agent_credentials()
            if credentials_path:
                logger.info(
                    "Customer agent credentials detected at '%s'", credentials_path
                )
                credentials = load_customer_credentials(credentials_path)
                loop = asyncio.get_running_loop()
                token = await loop.run_in_executor(
                    None,
                    exchange_user_token,
                    credentials,
                    resolved_user_token,
                    self._config.timeout,
                    app_tid,
                )
                return AuthResult(
                    access_token=token,
                    gateway_url=credentials.gateway_url,
                )

            # LoB flow
            if app_tid:
                logger.warning("app_tid parameter ignored for LoB agent flow")

            tenant = self._resolve_tenant_subdomain()
            token, gateway_url = await fetch_user_auth(resolved_user_token, tenant)
            return AuthResult(access_token=token, gateway_url=gateway_url)

        except AgentGatewaySDKError:
            raise
        except Exception as e:
            logger.exception("Unexpected error during user auth exchange")
            raise AgentGatewaySDKError(f"User auth exchange failed: {e}") from e

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
                print(f"{tool.name}: {tool.description}")
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
                auth = await self.get_system_auth(app_tid=app_tid)
                return await get_mcp_tools_customer(
                    credentials, auth.access_token, self._config.timeout
                )

            # LoB flow - requires tenant_subdomain
            if app_tid:
                logger.warning("app_tid parameter ignored for LoB agent flow")

            tenant = self._resolve_tenant_subdomain()
            auth = await self.get_system_auth()
            return await get_mcp_tools_lob(
                tenant, auth.access_token, self._config.timeout
            )

        except AgentGatewaySDKError:
            # Re-raise SDK errors as-is
            raise
        except Exception as e:
            logger.exception("Unexpected error during tool discovery")
            cause = _unwrap_exception_group(e)
            raise AgentGatewaySDKError(f"Tool discovery failed: {cause}") from e

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
                if user_token:
                    auth = await self.get_user_auth(user_token, app_tid)
                else:
                    # TODO: IBD workaround - use system token when user_token
                    # is not available. This bypasses principal propagation.
                    # Remove this fallback once IBD supports proper user token flow.
                    logger.warning(
                        "No user_token provided - using system token for tool "
                        "invocation. Principal propagation will NOT work."
                    )
                    auth = await self.get_system_auth(app_tid)

                return await call_mcp_tool_customer(
                    tool, auth.access_token, self._config.timeout, **kwargs
                )

            # LoB flow - requires user_token and tenant_subdomain
            if app_tid:
                logger.warning("app_tid parameter ignored for LoB agent flow")

            auth = await self.get_user_auth(user_token, app_tid)
            return await call_mcp_tool_lob(
                tool, auth.access_token, self._config.timeout, **kwargs
            )

        except AgentGatewaySDKError:
            # Re-raise SDK errors as-is
            raise
        except Exception as e:
            logger.exception("Unexpected error during tool invocation")
            cause = _unwrap_exception_group(e)
            raise AgentGatewaySDKError(
                f"Tool invocation failed for '{tool.name}': {cause}"
            ) from e


def _unwrap_exception_group(exc: BaseException) -> BaseException:
    """Unwrap nested ExceptionGroups to present meaningful error messages."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


def create_client(
    tenant_subdomain: str | Callable[[], str] | None = None,
    config: ClientConfig | None = None,
) -> AgentGatewayClient:
    """Create an Agent Gateway client for discovering and invoking MCP tools.

    Automatically detects agent type (LoB vs Customer) based on
    credential file presence.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
            Can be a string or a callable returning a string.
            Required for LoB agents, ignored for Customer agents.
        config: Client configuration. Uses defaults if not provided.

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

    Example (auth fetching):
        ```python
        from sap_cloud_sdk.agentgateway import create_client

        agw_client = create_client(tenant_subdomain="my-tenant")

        # Get auth for external use
        auth = await agw_client.get_system_auth()
        user_auth = await agw_client.get_user_auth(user_token="user-jwt")
        ```
    """
    return AgentGatewayClient(tenant_subdomain=tenant_subdomain, config=config)
