"""LoB agent flow - BTP Destination Service based.

LoB agents use BTP Destination Service for credential management:
- Phase 1 (discovery): Client credentials from destination
- Phase 2 (execution): Token exchange with user_token for principal propagation
"""

import asyncio
import logging
import os
import uuid

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from sap_cloud_sdk.destination import (
    create_client as create_destination_client,
    create_fragment_client,
    ConsumptionLevel,
    ConsumptionOptions,
    Label,
    ListOptions,
)

from sap_cloud_sdk.agentgateway._models import MCPTool
from sap_cloud_sdk.agentgateway.exceptions import MCPServerNotFoundError

logger = logging.getLogger(__name__)

# Shared label key for all managed-runtime fragment types
_LABEL_KEY = "sap-managed-runtime-type"

# Label values for fragment discovery
_MCP_LABEL_VALUE = "agw.mcp.server"
_IAS_LABEL_VALUE = "subscriber.ias"

_DESTINATION_INSTANCE = "default"

# HTTP timeout for MCP server requests (seconds)
_HTTP_TIMEOUT = 30.0


def _ias_dest_name() -> str:
    """Get IAS destination name based on landscape.

    Returns:
        Destination name in format: sap-managed-runtime-ias-{landscape}

    Raises:
        EnvironmentError: If APPFND_CONHOS_LANDSCAPE is not set.
    """
    landscape = os.environ.get("APPFND_CONHOS_LANDSCAPE")
    if not landscape:
        raise EnvironmentError(
            "APPFND_CONHOS_LANDSCAPE environment variable is not set"
        )
    return f"sap-managed-runtime-ias-{landscape}"


def _fetch_auth_token(
    dest_name: str,
    tenant_subdomain: str,
    options: ConsumptionOptions | None = None,
) -> str:
    """Fetch auth token from destination service.

    Args:
        dest_name: Destination name.
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
        options: Consumption options (fragment_name, user_token).

    Returns:
        Authorization header value.

    Raises:
        MCPServerNotFoundError: If no auth token is returned.
    """
    client = create_destination_client(instance=_DESTINATION_INSTANCE)
    dest = client.get_destination(
        dest_name,
        level=ConsumptionLevel.PROVIDER_SUBACCOUNT,
        options=options,
        tenant=tenant_subdomain,
    )

    if not dest or not dest.auth_tokens:
        raise MCPServerNotFoundError(
            f"No auth token returned for destination '{dest_name}'"
        )

    auth = dest.auth_tokens[0].http_header.get("value", "")
    if not auth:
        raise MCPServerNotFoundError(
            f"Empty Authorization header for destination '{dest_name}'"
        )

    return auth


def list_mcp_fragments(tenant_subdomain: str) -> list:
    """List destination fragments with MCP server label.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        List of fragments with sap-managed-runtime-type=agw.mcp.server label.
    """
    logger.debug("Fetching MCP fragments for tenant '%s'", tenant_subdomain)
    client = create_fragment_client(instance=_DESTINATION_INSTANCE)
    return client.list_instance_fragments(
        filter=ListOptions(
            filter_labels=[Label(key=_LABEL_KEY, values=[_MCP_LABEL_VALUE])]
        ),
        tenant=tenant_subdomain,
    )


def get_ias_fragment_name(tenant_subdomain: str) -> str:
    """Get the IAS fragment name for system (technical) token acquisition.

    Looks up the IAS fragment created during subscription by the
    sap-managed-runtime-type=subscriber.ias label.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        IAS fragment name.

    Raises:
        MCPServerNotFoundError: If no IAS fragment is found.
    """
    client = create_fragment_client(instance=_DESTINATION_INSTANCE)
    fragments = client.list_instance_fragments(
        filter=ListOptions(
            filter_labels=[Label(key=_LABEL_KEY, values=[_IAS_LABEL_VALUE])]
        ),
        tenant=tenant_subdomain,
    )
    if not fragments:
        raise MCPServerNotFoundError(
            f"No IAS fragment found (label {_LABEL_KEY}={_IAS_LABEL_VALUE}) "
            f"for tenant '{tenant_subdomain}'"
        )
    return fragments[0].name


async def get_system_auth(
    tenant_subdomain: str,
) -> str:
    """Get system-scoped auth (Phase 1 - client credentials).

    Looks up the IAS fragment (subscriber.ias label) and uses it to acquire
    a client-credentials token via BTP Destination Service.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        Authorization header value (e.g., "Bearer xxx").

    Raises:
        MCPServerNotFoundError: If no IAS fragment or auth token is found.
    """
    loop = asyncio.get_running_loop()

    def _fetch_system_auth_sync():
        ias_fragment_name = get_ias_fragment_name(tenant_subdomain)
        dest_name = _ias_dest_name()
        logger.debug(
            "Fetching system auth — destination: '%s', fragment: '%s', tenant: '%s'",
            dest_name,
            ias_fragment_name,
            tenant_subdomain,
        )

        options = ConsumptionOptions(
            fragment_name=ias_fragment_name,
            fragment_level=ConsumptionLevel.INSTANCE,
        )

        return _fetch_auth_token(dest_name, tenant_subdomain, options)

    return await loop.run_in_executor(None, _fetch_system_auth_sync)


async def get_user_auth(
    mcp_fragment_name: str,
    user_token: str,
    tenant_subdomain: str,
) -> str:
    """Get user-scoped auth (Phase 2 - token exchange).

    Args:
        mcp_fragment_name: MCP fragment name for token exchange.
        user_token: User's JWT for principal propagation.
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        Authorization header value with user identity embedded.

    Raises:
        MCPServerNotFoundError: If no auth token is returned.
    """
    loop = asyncio.get_running_loop()

    def _fetch_user_auth_sync():
        dest_name = _ias_dest_name()

        logger.info(
            "Exchanging user auth — destination: '%s', fragment: '%s', tenant: '%s'",
            dest_name,
            mcp_fragment_name,
            tenant_subdomain,
        )

        options = ConsumptionOptions(
            user_token=user_token,
            fragment_name=mcp_fragment_name,
            fragment_level=ConsumptionLevel.INSTANCE,
        )

        return _fetch_auth_token(dest_name, tenant_subdomain, options)

    return await loop.run_in_executor(None, _fetch_user_auth_sync)


async def list_server_tools(
    dest_url: str, system_auth: str, fragment_name: str
) -> list[MCPTool]:
    """List tools from a single MCP server.

    Args:
        dest_url: MCP endpoint URL.
        system_auth: Authorization header for the request.
        fragment_name: Fragment name for reference.

    Returns:
        List of MCPTool objects from this server.
    """
    async with httpx.AsyncClient(
        headers={"Authorization": system_auth, "x-correlation-id": str(uuid.uuid4())},
        timeout=_HTTP_TIMEOUT,
    ) as http_client:
        async with streamable_http_client(dest_url, http_client=http_client) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                init_result = await session.initialize()
                server_name = (
                    init_result.serverInfo.name
                    if init_result
                    and init_result.serverInfo
                    and init_result.serverInfo.name
                    else fragment_name
                )
                result = await session.list_tools()
                return [
                    MCPTool(
                        name=t.name,
                        server_name=server_name,
                        description=t.description or "",
                        input_schema=t.inputSchema or {},
                        url=dest_url,
                        fragment_name=fragment_name,
                    )
                    for t in result.tools
                ]


async def get_mcp_tools_lob(
    tenant_subdomain: str,
) -> list[MCPTool]:
    """List all MCP tools using LoB flow (destination-based).

    Uses Phase 1 auth (client-scoped) via BTP Destination Service.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        List of MCPTool objects from all MCP servers.
    """
    tools: list[MCPTool] = []
    loop = asyncio.get_running_loop()

    logger.info("Listing MCP fragments for tenant '%s'", tenant_subdomain)

    fragments = await loop.run_in_executor(None, list_mcp_fragments, tenant_subdomain)

    if not fragments:
        logger.debug(
            "No MCP fragments found (label %s=%s)", _LABEL_KEY, _MCP_LABEL_VALUE
        )
        return tools

    for fragment in fragments:
        fragment_name = fragment.name
        mcp_url = fragment.properties.get("URL") or fragment.properties.get("url")

        if not mcp_url:
            logger.warning(
                "Fragment '%s' has no URL property — skipping", fragment_name
            )
            continue

        try:
            system_auth = await get_system_auth(tenant_subdomain)
            server_tools = await list_server_tools(mcp_url, system_auth, fragment_name)
            tools.extend(server_tools)
            logger.debug(
                "Loaded %d tool(s) from fragment '%s'",
                len(server_tools),
                fragment_name,
            )
        except Exception:
            logger.exception(
                "Failed to load tools from fragment '%s' — skipping",
                fragment_name,
            )

    logger.info("Loaded %d MCP tool(s) from %d fragment(s)", len(tools), len(fragments))
    return tools


async def call_mcp_tool_lob(
    tool: MCPTool,
    user_token: str,
    tenant_subdomain: str,
    **kwargs,
) -> str:
    """Invoke an MCP tool using LoB flow (destination-based).

    Uses Phase 2 auth (user-scoped) via token exchange.
    Principal propagation ensures LoB systems see user identity.

    Args:
        tool: MCPTool object (from list_mcp_tools).
        user_token: User's JWT for principal propagation.
        tenant_subdomain: Tenant subdomain for token exchange.
        **kwargs: Tool input parameters.

    Returns:
        Tool execution result as string.

    Raises:
        MCPServerNotFoundError: If destination/auth fails.
    """
    if not tool.fragment_name:
        raise MCPServerNotFoundError(
            f"Tool '{tool.name}' missing fragment_name for LoB invocation"
        )
    user_auth = await get_user_auth(tool.fragment_name, user_token, tenant_subdomain)

    async with httpx.AsyncClient(
        headers={"Authorization": user_auth, "x-correlation-id": str(uuid.uuid4())},
        timeout=_HTTP_TIMEOUT,
    ) as http_client:
        async with streamable_http_client(tool.url, http_client=http_client) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool.name, kwargs)
                if not result.content:
                    logger.warning("Tool '%s' returned empty content", tool.name)
                    return ""
                first = result.content[0]
                return str(getattr(first, "text", ""))
