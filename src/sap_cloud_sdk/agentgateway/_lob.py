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
from sap_cloud_sdk.agentgateway._token_cache import _TokenCache
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError, MCPServerNotFoundError

logger = logging.getLogger(__name__)

# Shared label key for all managed-runtime fragment types
_LABEL_KEY = "sap-managed-runtime-type"

# Label values for fragment discovery
_MCP_LABEL_VALUE = "agw.mcp.server"
_IAS_LABEL_VALUE = "subscriber.ias"

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
    cache: _TokenCache,
) -> str:
    """Get system-scoped auth (Phase 1 - client credentials).

    Checks the token cache first. On a miss, looks up the IAS fragment
    (subscriber.ias label) and acquires a client-credentials token via
    BTP Destination Service, then caches the result.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
        cache: Token cache shared across calls.

    Returns:
        Authorization header value (e.g., "Bearer xxx").

    Raises:
        MCPServerNotFoundError: If no IAS fragment or auth token is found.
    """
    cached = cache.get_system_token(tenant_subdomain)
    if cached:
        logger.debug("System token cache hit for tenant '%s'", tenant_subdomain)
        return cached

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

    auth = await loop.run_in_executor(None, _fetch_system_auth_sync)
    expires_at = cache.compute_expires_at_from_bearer(auth)
    cache.set_system_token(auth, expires_at, tenant_subdomain)
    return auth


async def get_user_auth(
    mcp_fragment_name: str,
    user_token: str,
    tenant_subdomain: str,
    cache: _TokenCache,
) -> str:
    """Get user-scoped auth (Phase 2 - token exchange).

    Checks the token cache first. On a miss, exchanges the user token via
    BTP Destination Service, then caches the result.

    Cache key is scoped to (user_token, mcp_fragment_name, tenant_subdomain)
    since different fragments may yield differently-scoped tokens.

    Args:
        mcp_fragment_name: MCP fragment name for token exchange.
        user_token: User's JWT for principal propagation.
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
        cache: Token cache shared across calls.

    Returns:
        Authorization header value with user identity embedded.

    Raises:
        MCPServerNotFoundError: If no auth token is returned.
    """
    scope_key = f"{mcp_fragment_name}|{tenant_subdomain}"
    cached = cache.get_user_token(user_token, scope_key)
    if cached:
        logger.debug(
            "User token cache hit for tenant '%s', fragment '%s'",
            tenant_subdomain,
            mcp_fragment_name,
        )
        return cached

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

    auth = await loop.run_in_executor(None, _fetch_user_auth_sync)
    expires_at = cache.compute_expires_at_from_bearer(auth)
    cache.set_user_token(user_token, auth, expires_at, scope_key)
    return auth


async def list_server_tools(
    dest_url: str, system_auth: str, fragment_name: str, timeout: float
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
    timeout: float,
    cache: _TokenCache,
) -> list[MCPTool]:
    """List all MCP tools using LoB flow (destination-based).

    Uses Phase 1 auth (client-scoped) via BTP Destination Service.
    On a 401 from an MCP server, invalidates the cached system token and
    retries once before skipping the fragment.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
        timeout: HTTP timeout in seconds.
        cache: Token cache shared across calls.

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

    system_auth = None

    async def _refetch_system_auth() -> str:
        return await get_system_auth(tenant_subdomain, cache)

    for fragment in fragments:
        fragment_name = fragment.name
        mcp_url = fragment.properties.get("URL") or fragment.properties.get("url")

        if not mcp_url:
            logger.warning(
                "Fragment '%s' has no URL property — skipping", fragment_name
            )
            continue

        for attempt in (1, 2):
            if not system_auth:
                # Auth failure here is immediately fatal — same token is needed for
                # all fragments, so there is no point continuing.
                system_auth = await _refetch_system_auth()

            try:
                server_tools = await list_server_tools(
                    mcp_url, system_auth, fragment_name, timeout
                )
                tools.extend(server_tools)
                logger.debug(
                    "Loaded %d tool(s) from fragment '%s'",
                    len(server_tools),
                    fragment_name,
                )
            except Exception as exc:
                unwrapped = _unwrap_exception_group(exc)
                if _is_unauthorized(unwrapped) and attempt == 1:
                    logger.info(
                        "401 from '%s' — invalidating cached system token and retrying",
                        fragment_name,
                    )
                    cache.invalidate_system_token(tenant_subdomain)
                    system_auth = None
                    continue
                logger.exception(
                    "Failed to load tools from fragment '%s' — skipping", fragment_name
                )
            break

    logger.info("Loaded %d MCP tool(s) from %d fragment(s)", len(tools), len(fragments))
    return tools


async def call_mcp_tool_lob(
    tool: MCPTool,
    user_token: str,
    tenant_subdomain: str,
    timeout: float,
    cache: _TokenCache,
    **kwargs,
) -> str:
    """Invoke an MCP tool using LoB flow (destination-based).

    Uses Phase 2 auth (user-scoped) via token exchange.
    Principal propagation ensures LoB systems see user identity.
    On a 401, invalidates the cached user token and retries once.

    Args:
        tool: MCPTool object (from list_mcp_tools).
        user_token: User's JWT for principal propagation.
        tenant_subdomain: Tenant subdomain for token exchange.
        timeout: HTTP timeout in seconds.
        cache: Token cache shared across calls.
        **kwargs: Tool input parameters.

    Returns:
        Tool execution result as string.

    Raises:
        MCPServerNotFoundError: If destination/auth fails.
        AgentGatewaySDKError: If tool invocation fails after 401 retry.
    """
    if not tool.fragment_name:
        raise MCPServerNotFoundError(
            f"Tool '{tool.name}' missing fragment_name for LoB invocation"
        )

    scope_key = f"{tool.fragment_name}|{tenant_subdomain}"
    last_exc: Exception | None = None

    for attempt in (1, 2):
        user_auth = await get_user_auth(
            tool.fragment_name, user_token, tenant_subdomain, cache
        )
        try:
            async with httpx.AsyncClient(
                headers={
                    "Authorization": user_auth,
                    "x-correlation-id": str(uuid.uuid4()),
                },
                timeout=timeout,
            ) as http_client:
                async with streamable_http_client(
                    tool.url, http_client=http_client
                ) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool.name, kwargs)
                        if not result.content:
                            logger.warning(
                                "Tool '%s' returned empty content", tool.name
                            )
                            return ""
                        first = result.content[0]
                        return str(getattr(first, "text", ""))
        except Exception as exc:
            unwrapped = _unwrap_exception_group(exc)
            if _is_unauthorized(unwrapped) and attempt == 1:
                logger.info(
                    "401 from MCP server for tool '%s' — invalidating cached token and retrying",
                    tool.name,
                )
                cache.invalidate_user_token(user_token, scope_key)
                last_exc = exc
                continue
            raise

    # Defensive — should not be reachable; second attempt either returns or raises.
    raise AgentGatewaySDKError(
        f"Tool invocation for '{tool.name}' failed after 401 retry: {last_exc}"
    )


def _unwrap_exception_group(exc: BaseException) -> BaseException:
    """Unwrap nested ExceptionGroups to find the underlying cause."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


def _is_unauthorized(exc: BaseException) -> bool:
    """Detect a 401 response from the MCP server (httpx-based)."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response is not None and exc.response.status_code == 401
    return False
