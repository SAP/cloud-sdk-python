"""LoB agent flow - BTP Destination Service based.

LoB agents use BTP Destination Service for credential management:
- Phase 1 (discovery): Client credentials from destination (subscriber.ias fragment)
- Phase 2 (execution): Token exchange with user_token (subscriber.ias.user fragment)
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
_IAS_USER_LABEL_VALUE = "subscriber.ias.user"

_DESTINATION_INSTANCE = "default"


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
) -> tuple[str, str]:
    """Fetch auth token and gateway URL from destination service.

    Extracts the raw JWT from the Authorization header value returned by the
    destination service (e.g. strips the "Bearer " prefix from "Bearer <jwt>"),
    and the gateway URL from the destination's URL property.

    Args:
        dest_name: Destination name.
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
        options: Consumption options (fragment_name, user_token).

    Returns:
        Tuple of (raw_jwt, gateway_url).

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

    auth_token = dest.auth_tokens[0]
    header_value = auth_token.http_header.get("value") or ""
    if not header_value:
        raise MCPServerNotFoundError(f"Empty auth header for destination '{dest_name}'")

    # Strip "Bearer " prefix — AuthResult.access_token is always a raw JWT
    raw_token = header_value.removeprefix("Bearer ").strip()

    gateway_url = (dest.url or "").rstrip("/")

    return raw_token, gateway_url


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


def get_ias_user_fragment_name(tenant_subdomain: str) -> str:
    """Get the IAS user fragment name for token exchange (principal propagation).

    Looks up the IAS user fragment created during subscription by the
    sap-managed-runtime-type=subscriber.ias.user label.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        IAS user fragment name.

    Raises:
        MCPServerNotFoundError: If no IAS user fragment is found.
    """
    client = create_fragment_client(instance=_DESTINATION_INSTANCE)
    fragments = client.list_instance_fragments(
        filter=ListOptions(
            filter_labels=[Label(key=_LABEL_KEY, values=[_IAS_USER_LABEL_VALUE])]
        ),
        tenant=tenant_subdomain,
    )
    if not fragments:
        raise MCPServerNotFoundError(
            f"No IAS user fragment found (label {_LABEL_KEY}={_IAS_USER_LABEL_VALUE}) "
            f"for tenant '{tenant_subdomain}'"
        )
    return fragments[0].name


async def fetch_system_auth(
    tenant_subdomain: str,
) -> tuple[str, str]:
    """Fetch system-scoped auth (Phase 1 - client credentials).

    Looks up the IAS fragment (subscriber.ias label) and uses it to acquire
    a client-credentials token via BTP Destination Service.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        Tuple of (raw_access_token, gateway_url).

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


async def fetch_user_auth(
    user_token: str,
    tenant_subdomain: str,
) -> tuple[str, str]:
    """Fetch user-scoped auth (Phase 2 - token exchange).

    Looks up the IAS user fragment (subscriber.ias.user label) and uses it
    together with the user_token to perform a token exchange via BTP
    Destination Service.

    Args:
        user_token: User's JWT for principal propagation.
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        Tuple of (raw_access_token, gateway_url).

    Raises:
        MCPServerNotFoundError: If no IAS user fragment or auth token is found.
    """
    loop = asyncio.get_running_loop()

    def _fetch_user_auth_sync():
        ias_user_fragment_name = get_ias_user_fragment_name(tenant_subdomain)
        dest_name = _ias_dest_name()

        logger.info(
            "Exchanging user auth — destination: '%s', fragment: '%s', tenant: '%s'",
            dest_name,
            ias_user_fragment_name,
            tenant_subdomain,
        )

        options = ConsumptionOptions(
            user_token=user_token,
            fragment_name=ias_user_fragment_name,
            fragment_level=ConsumptionLevel.INSTANCE,
        )

        return _fetch_auth_token(dest_name, tenant_subdomain, options)

    return await loop.run_in_executor(None, _fetch_user_auth_sync)


async def list_server_tools(
    dest_url: str, auth_token: str, fragment_name: str, timeout: float
) -> list[MCPTool]:
    """List tools from a single MCP server.

    Args:
        dest_url: MCP endpoint URL.
        auth_token: Raw access token for the request.
        fragment_name: Fragment name for reference.

    Returns:
        List of MCPTool objects from this server.
    """
    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {auth_token}",
            "x-correlation-id": str(uuid.uuid4()),
        },
        timeout=timeout,
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
    system_token: str,
    timeout: float,
) -> list[MCPTool]:
    """List all MCP tools using LoB flow (destination-based).

    Uses a pre-fetched system token for authentication against MCP servers.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
        system_token: Pre-fetched raw system token (from get_system_auth).
        timeout: HTTP timeout in seconds for MCP server calls.

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
            server_tools = await list_server_tools(
                mcp_url, system_token, fragment_name, timeout
            )
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
    user_auth_token: str,
    timeout: float,
    **kwargs,
) -> str:
    """Invoke an MCP tool using LoB flow (destination-based).

    Uses a pre-fetched user token for principal propagation.

    Args:
        tool: MCPTool object (from list_mcp_tools).
        user_auth_token: Pre-fetched raw user token (from get_user_auth).
        timeout: HTTP timeout in seconds for the MCP server call.
        **kwargs: Tool input parameters.

    Returns:
        Tool execution result as string.
    """
    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {user_auth_token}",
            "x-correlation-id": str(uuid.uuid4()),
        },
        timeout=timeout,
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
