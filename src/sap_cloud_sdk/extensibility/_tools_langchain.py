"""LangChain tool loading helpers for SAP Cloud SDK extensibility."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def load_extension_tools_langchain(
    ext_impl: Any,
    agw_client: Any,
    inbound_token: str,
    *,
    tool_wrapper: Optional[Any] = None,
) -> list:
    """Fetch extension MCP tools via Agent Gateway for LangChain agents.

    Convenience wrapper around :func:`resolve_mcp_servers` for LangChain
    agents.  Connects to each MCP server, filters tools to those listed in
    ``server.tool_names``, and returns the combined tool list.

    Failures per MCP server are logged as warnings and skipped — extension
    tools are optional and must not block core agent functionality.

    Args:
        ext_impl: :class:`~sap_cloud_sdk.extensibility.ExtensionCapabilityImplementation`
            returned by :meth:`~sap_cloud_sdk.extensibility.ExtensibilityClient.get_extension_capability_implementation`.
        agw_client: Agent Gateway client (created via
            ``sap_cloud_sdk.agentgateway.create_client``).  The caller is
            responsible for creating it with the correct ``tenant_subdomain``.
        inbound_token: Raw inbound bearer token used for AGW user auth exchange.
        tool_wrapper: Optional ``ToolCallInterceptor`` to attach to the
            ``MultiServerMCPClient``.  When ``None`` (default), an
            :class:`~sap_cloud_sdk.extensibility.ExtensionTelemetryInterceptor`
            is created automatically from ``ext_impl``.

    Returns:
        List of LangChain tools loaded from all reachable MCP servers.
        Returns an empty list if auth fails or no servers are configured.

    Example::

        from sap_cloud_sdk.agentgateway import create_client as create_agw_client
        from sap_cloud_sdk.extensibility import load_extension_tools_langchain

        agw_client = create_agw_client(tenant_subdomain=tenant_subdomain)
        tools = await load_extension_tools_langchain(ext_impl, agw_client, inbound_token)
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore[import-untyped]  # ty: ignore[unresolved-import]

    from sap_cloud_sdk.extensibility._langchain import ExtensionTelemetryInterceptor
    from sap_cloud_sdk.extensibility._mcp_servers import resolve_mcp_servers

    if not ext_impl or not ext_impl.mcp_servers:
        return []

    params = await resolve_mcp_servers(ext_impl, agw_client, inbound_token)
    if not params:
        return []

    tool_name_to_server: dict[str, Any] = {
        name: server
        for server in ext_impl.mcp_servers
        for name in (server.tool_names or [])
    }

    interceptor = tool_wrapper or ExtensionTelemetryInterceptor(ext_impl=ext_impl)
    ext_tools: list = []

    for server, conn in params:
        try:
            mcp_client = MultiServerMCPClient(
                {server.ord_id: {**conn, "transport": "streamable_http"}},
                tool_interceptors=[interceptor],
            )
            mcp_tools = await mcp_client.get_tools()
            filtered = [t for t in mcp_tools if t.name in tool_name_to_server]
            ext_tools.extend(filtered)
            logger.info(
                "Loaded %d extension tool(s) from MCP server %s",
                len(filtered),
                server.ord_id,
            )
        except Exception as exc:
            logger.warning(
                "Failed to load MCP tools from %s — skipping: %s",
                server.ord_id,
                exc,
            )

    logger.info("Found %d extension tool(s) total", len(ext_tools))
    return ext_tools
