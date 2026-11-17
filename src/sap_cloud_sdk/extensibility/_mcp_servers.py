"""Framework-agnostic MCP server connection parameter resolution."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def resolve_mcp_servers(
    ext_impl: Any,
    agw_client: Any,
    inbound_token: str,
) -> list[tuple[Any, dict[str, Any]]]:
    """Resolve Agent Gateway connection parameters for each MCP server.

    Performs token exchange via the Agent Gateway and builds the URL and auth
    headers for every MCP server listed in ``ext_impl.mcp_servers``.  The
    caller uses these parameters to create whatever MCP client their framework
    provides.

    This is the framework-agnostic primitive.
    :func:`load_extension_tools_langchain` is a thin convenience wrapper on
    top of this function for LangChain agents.

    Args:
        ext_impl: :class:`~sap_cloud_sdk.extensibility.ExtensionCapabilityImplementation`
            returned by
            :meth:`~sap_cloud_sdk.extensibility.ExtensibilityClient.get_extension_capability_implementation`.
        agw_client: Agent Gateway client (created via
            ``sap_cloud_sdk.agentgateway.create_client``).
        inbound_token: Raw inbound bearer token for AGW user auth exchange.

    Returns:
        List of ``(McpServer, connection_params)`` pairs where
        ``connection_params`` is a dict with ``"url"`` and ``"headers"`` keys.
        Returns an empty list if auth fails or no servers are configured.

    Example — PydanticAI::

        from pydantic_ai.mcp import MCPServerStreamableHTTP
        from sap_cloud_sdk.extensibility import resolve_mcp_servers

        params = await resolve_mcp_servers(ext_impl, agw_client, inbound_token)
        mcp_servers = [
            MCPServerStreamableHTTP(url=conn["url"], headers=conn["headers"])
            for _, conn in params
        ]

    Example — per-server audit wrapping (LangChain)::

        from sap_cloud_sdk.extensibility import resolve_mcp_servers

        params = await resolve_mcp_servers(ext_impl, agw_client, inbound_token)
        tools = []
        for server, conn in params:
            raw = await fetch_tools(conn)  # your framework's MCP client
            tools.extend(wrap_for_audit(raw, server.ord_id))
    """
    if not ext_impl or not ext_impl.mcp_servers:
        return []

    try:
        auth = await agw_client.get_user_auth(user_token=inbound_token)
    except Exception as exc:
        logger.error("Agent Gateway user auth fetch failed: %s", exc)
        return []

    auth_headers = {"Authorization": f"Bearer {auth.access_token}"}
    agw_host = auth.gateway_url

    result: list[tuple[Any, dict[str, Any]]] = []
    for server in ext_impl.mcp_servers:
        gateway_url = f"{agw_host}/v1/mcp/{server.ord_id}/{server.global_tenant_id}"
        result.append((server, {"url": gateway_url, "headers": auth_headers}))

    return result
