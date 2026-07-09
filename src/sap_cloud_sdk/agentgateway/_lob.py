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
    ConsumptionLevel,
    ConsumptionOptions,
)
from sap_cloud_sdk.core.telemetry import Module

from sap_cloud_sdk.agentgateway._fragments import (
    LABEL_KEY,
    FragmentLabel,
    get_ias_fragment_name,
    get_ias_user_fragment_name,
    list_mcp_fragments,
    list_a2a_fragments,
)
from sap_cloud_sdk.agentgateway._models import Agent, AgentCard, MCPTool
from sap_cloud_sdk.agentgateway._token_cache import _GatewayUrlCache, _TokenCache
from sap_cloud_sdk.agentgateway.exceptions import (
    AgentGatewaySDKError,
    MCPServerNotFoundError,
)

logger = logging.getLogger(__name__)

_DESTINATION_INSTANCE = "default"


def _system_scope_key(tenant_subdomain: str) -> str:
    """Build the cache scope key for tenant-scoped system auth."""
    return f"lob-system::{tenant_subdomain}"


def _user_scope_key(tenant_subdomain: str) -> str:
    """Build the cache scope key for tenant-scoped user auth."""
    return f"lob-user::{tenant_subdomain}"


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
    client = create_destination_client(
        instance=_DESTINATION_INSTANCE,
        _telemetry_source=Module.AGENTGATEWAY,
    )
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


def get_ias_client_id_lob() -> str:
    """Read the IAS client ID from the IAS destination properties (LoB flow).

    Fetches the IAS destination (``sap-managed-runtime-ias-{landscape}``)
    at provider subaccount level with ``$skipTokenRetrieval=true`` so only
    destination properties are returned — no auth token exchange is performed.

    Returns:
        The IAS client ID string, or ``""`` if the ``clientId`` property is absent.

    Raises:
        EnvironmentError: If ``APPFND_CONHOS_LANDSCAPE`` is not set.
        AgentGatewaySDKError: If the IAS destination is not found.
        Any exception raised by the destination client.
    """
    dest_name = _ias_dest_name()
    client = create_destination_client(
        instance=_DESTINATION_INSTANCE,
        _telemetry_source=Module.AGENTGATEWAY,
    )
    dest = client.get_destination(
        dest_name,
        level=ConsumptionLevel.PROVIDER_SUBACCOUNT,
        options=ConsumptionOptions(skip_token_retrieval=True),
    )
    if not dest:
        raise AgentGatewaySDKError(f"IAS destination '{dest_name}' not found")
    return dest.properties.get("clientId", "")


async def fetch_system_auth(
    tenant_subdomain: str,
    token_cache: _TokenCache | None = None,
    gateway_url_cache: _GatewayUrlCache | None = None,
) -> tuple[str, str]:
    """Fetch system-scoped auth (Phase 1 - client credentials).

    Looks up the IAS fragment (subscriber.ias label) and uses it to acquire
    a client-credentials token via BTP Destination Service.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
        token_cache: Optional token cache used to reuse still-valid system
            tokens.
        gateway_url_cache: Optional cache for gateway URLs associated with the
            cached system-token scope.

    Returns:
        Tuple of `(raw_access_token, gateway_url)`, fetched or served from cache.

    Raises:
        MCPServerNotFoundError: If no IAS fragment or auth token is found.
    """
    scope_key = _system_scope_key(tenant_subdomain)
    if (token_cache is None) != (gateway_url_cache is None):
        raise ValueError(
            "token_cache and gateway_url_cache must both be provided or both be None"
        )
    if token_cache and gateway_url_cache is not None:
        cached_token = token_cache.get_system_token(scope_key)
        cached_gateway_url = gateway_url_cache.get(scope_key)
        if cached_token and cached_gateway_url:
            logger.debug("Using cached system auth for tenant '%s'", tenant_subdomain)
            return cached_token, cached_gateway_url

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

    token, gateway_url = await loop.run_in_executor(None, _fetch_system_auth_sync)

    if token_cache:
        token_cache.set_system_token(
            token,
            token_cache.compute_expires_at_from_bearer(token),
            scope_key,
        )
    if gateway_url_cache is not None:
        gateway_url_cache[scope_key] = gateway_url

    return token, gateway_url


async def fetch_user_auth(
    user_token: str,
    tenant_subdomain: str,
    token_cache: _TokenCache | None = None,
    gateway_url_cache: _GatewayUrlCache | None = None,
) -> tuple[str, str]:
    """Fetch user-scoped auth (Phase 2 - token exchange).

    Looks up the IAS user fragment (subscriber.ias.user label) and uses it
    together with the user_token to perform a token exchange via BTP
    Destination Service.

    Args:
        user_token: User's JWT for principal propagation.
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
        token_cache: Optional token cache used to reuse still-valid exchanged
            user tokens.
        gateway_url_cache: Optional cache for gateway URLs associated with the
            cached user-token scope.

    Returns:
        Tuple of `(raw_access_token, gateway_url)`, fetched or served from cache.

    Raises:
        MCPServerNotFoundError: If no IAS user fragment or auth token is found.
    """
    scope_key = _user_scope_key(tenant_subdomain)
    if (token_cache is None) != (gateway_url_cache is None):
        raise ValueError(
            "token_cache and gateway_url_cache must both be provided or both be None"
        )
    if token_cache and gateway_url_cache is not None:
        cached_token = token_cache.get_user_token(user_token, scope_key)
        cached_gateway_url = gateway_url_cache.get(scope_key)
        if cached_token and cached_gateway_url:
            logger.debug("Using cached user auth for tenant '%s'", tenant_subdomain)
            return cached_token, cached_gateway_url

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

    token, gateway_url = await loop.run_in_executor(None, _fetch_user_auth_sync)

    if token_cache:
        token_cache.set_user_token(
            user_token,
            token,
            token_cache.compute_expires_at_from_bearer(token),
            scope_key,
        )
    if gateway_url_cache is not None:
        gateway_url_cache[scope_key] = gateway_url

    return token, gateway_url


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
            "No MCP fragments found (label %s=%s)", LABEL_KEY, FragmentLabel.MCP.value
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


async def _fetch_agent_card(
    fragment_url: str,
    auth_token: str,
    timeout: float,
) -> AgentCard:
    """Fetch agent card from the A2A well-known endpoint.

    URL: {fragment_url}/.well-known/agent-card.json

    Args:
        fragment_url: Base URL from the A2A fragment's URL property.
        auth_token: Raw access token for authentication.
        timeout: HTTP timeout in seconds.

    Returns:
        AgentCard with the full parsed response payload.

    Raises:
        AgentGatewaySDKError: If the request fails or returns a non-200 status.
    """
    url = f"{fragment_url.rstrip('/')}/.well-known/agent-card.json"
    logger.debug("Fetching agent card from '%s'", url)

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {auth_token}",
            "x-correlation-id": str(uuid.uuid4()),
        },
        timeout=timeout,
    ) as client:
        try:
            response = await client.get(url)
        except httpx.RequestError as e:
            raise AgentGatewaySDKError(
                f"Agent card request failed for '{fragment_url}': {e}"
            ) from e

    if response.status_code != 200:
        raise AgentGatewaySDKError(
            f"Agent card request returned status {response.status_code} "
            f"for '{fragment_url}': {response.text[:200]}"
        )

    try:
        payload = response.json()
    except Exception as e:
        raise AgentGatewaySDKError(
            f"Failed to parse agent card JSON for '{fragment_url}': {e}"
        ) from e

    return AgentCard(raw=payload)


def _ord_id_from_url(url: str) -> str:
    """Extract the ORD ID from an A2A fragment URL.

    A2A fragment URLs follow the pattern:
        https://{gateway-host}/v1/a2a/{ordId}/{globalTenantId}

    The ORD ID is the second-to-last non-empty path segment.

    Returns an empty string if the URL path has fewer than two segments.
    """
    from urllib.parse import urlparse

    path_segments = [s for s in urlparse(url).path.split("/") if s]
    return path_segments[-2] if len(path_segments) >= 2 else ""


async def get_agent_cards_lob(
    tenant_subdomain: str,
    system_token: str,
    timeout: float,
    agent_names: list[str] | None = None,
    ord_ids: list[str] | None = None,
) -> list[Agent]:
    """List A2A agents and their agent cards using LoB flow.

    Discovers A2A fragments (label agw.a2a.server), optionally filters by
    ORD ID before fetching, fetches each agent card, then optionally filters
    by agent card name.

    Fragment properties used:
        URL: Base URL of the A2A agent (required).
            The agent card is fetched at {URL}/.well-known/agent-card.json.
            The ORD ID is extracted from the second-to-last URL path segment.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.
        system_token: Pre-fetched raw system token for authentication.
        timeout: HTTP timeout in seconds.
        agent_names: Optional list of agent card names to include (matched
            against the `name` field in the fetched agent card JSON).
            Applied after fetching. If empty or None, all are included.
        ord_ids: Optional list of ORD IDs to include (extracted from URL).
            Applied before fetching. If empty or None, all are included.

    Returns:
        List of Agent objects, each containing ORD ID and fetched AgentCard.
    """
    loop = asyncio.get_running_loop()

    logger.info("Listing A2A fragments for tenant '%s'", tenant_subdomain)
    fragments = await loop.run_in_executor(None, list_a2a_fragments, tenant_subdomain)

    if not fragments:
        logger.debug(
            "No A2A fragments found (label %s=%s)", LABEL_KEY, FragmentLabel.A2A.value
        )
        return []

    # Pre-fetch filter: ORD ID is extractable from the URL without fetching the card
    if ord_ids:
        ord_ids_set = set(ord_ids)
        fragments = [
            f
            for f in fragments
            if _ord_id_from_url(
                {k.lower(): v for k, v in f.properties.items()}.get("url", "")
            )
            in ord_ids_set
        ]

    agents: list[Agent] = []

    for fragment in fragments:
        fragment_name = fragment.name
        props_lower = {k.lower(): v for k, v in fragment.properties.items()}
        fragment_url = props_lower.get("url")

        if not fragment_url:
            logger.warning(
                "A2A fragment '%s' missing 'URL' property — skipping (properties: %s)",
                fragment_name,
                list(fragment.properties.keys()),
            )
            continue

        ord_id = _ord_id_from_url(fragment_url)
        if not ord_id:
            logger.warning(
                "A2A fragment '%s' could not extract ordId from URL '%s' — skipping",
                fragment_name,
                fragment_url,
            )
            continue

        try:
            card = await _fetch_agent_card(fragment_url, system_token, timeout)
            agents.append(Agent(ord_id=ord_id, agent_card=card))
            logger.debug("Fetched agent card for fragment '%s'", fragment_name)
        except Exception:
            logger.exception(
                "Failed to fetch agent card for fragment '%s' — skipping", fragment_name
            )

    # Post-fetch filter: agent card name is only known after fetching
    if agent_names:
        agent_names_set = set(agent_names)
        agents = [a for a in agents if a.agent_card.raw.get("name") in agent_names_set]

    logger.info(
        "Fetched %d agent card(s) from %d A2A fragment(s)", len(agents), len(fragments)
    )
    return agents
