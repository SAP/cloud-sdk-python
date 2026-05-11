"""ORD integration helpers for extensibility.

Provides utilities to inject extension capability MCP servers into the
ORD (Open Resource Discovery) document at runtime.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sap_cloud_sdk.extensibility.client import ExtensibilityClient
from sap_cloud_sdk.extensibility._models import ExtensionCapabilityImplementation

logger = logging.getLogger(__name__)


def _derive_mcp_name_from_ord_id(ord_id: str) -> str:
    """Derive a readable MCP server name from its ordId.

    ordId format: {namespace}:apiResource:{resource-name}:v1

    Returns the namespace short name (first segment before any dot) in title case.
    Example: "sap.s4:apiResource:s4bpintelmcp:v1" -> "S4"

    Args:
        ord_id: The MCP server ordId.

    Returns:
        A readable name derived from the ordId.
    """
    namespace = ord_id.split(":")[0] if ":" in ord_id else ord_id
    namespace_short = namespace.split(".")[-1] if namespace else "unknown"
    return namespace_short.replace("_", " ").replace("-", " ").title()


def _map_capability_to_integration_dependencies(
    capability_impl: ExtensionCapabilityImplementation,
    agent: Optional[dict] = None,
    base_integration_deps: Optional[list[dict]] = None,
) -> list[dict]:
    """Map a capability implementation to ORD IntegrationDependency structure.

    Args:
        capability_impl: ExtensionCapabilityImplementation from the extensibility client.
        agent: The agent dict from the ORD document to derive namespace and partOfPackage.
        base_integration_deps: List of existing document-level integration dependencies
            to check against for duplicate MCP servers.

    Returns:
        List of IntegrationDependency dicts ready for ORD injection.
    """
    mcp_servers = capability_impl.mcp_servers if capability_impl else []
    if not mcp_servers:
        return []

    base_api_resource_ord_ids: set = set()
    if base_integration_deps:
        for base_dep in base_integration_deps:
            for aspect in base_dep.get("aspects", []):
                for api_resource in aspect.get("apiResources", []):
                    base_api_resource_ord_ids.add(api_resource["ordId"])

    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    namespace = ""
    part_of_package = None
    if agent:
        agent_ord_id = agent.get("ordId", "")
        namespace = agent_ord_id.split(":")[0] if agent_ord_id else ""
        part_of_package = agent.get("partOfPackage")

    aspects = []
    for mcp_server in mcp_servers:
        if mcp_server.ord_id in base_api_resource_ord_ids:
            logger.debug(
                "Skipping MCP %s - already in base integration dependencies",
                mcp_server.ord_id,
            )
            continue

        mcp_name = _derive_mcp_name_from_ord_id(mcp_server.ord_id)
        aspect = {
            "title": f"{mcp_name} Extension MCP",
            "mandatory": False,
            "apiResources": [
                {
                    "ordId": mcp_server.ord_id,
                }
            ],
        }
        aspects.append(aspect)

    if not aspects:
        logger.info(
            "All extended MCP servers already present in base integration dependencies"
        )
        return []

    integration_dependency = {
        "ordId": f"{namespace}:integrationDependency:extension-mcp:v1",
        "title": "Extension MCP Servers",
        "version": "1.0.0",
        "releaseStatus": "active",
        "visibility": "public",
        "mandatory": False,
        "partOfPackage": part_of_package,
        "lastUpdate": current_time,
        "aspects": aspects,
    }

    return [integration_dependency]


def fetch_extension_integration_dependencies(
    ext_client: ExtensibilityClient,
    capability_id: str = "default",
    agent: Optional[dict] = None,
    base_integration_deps: Optional[list[dict]] = None,
    tenant: Optional[str] = None,
) -> list[dict]:
    """Fetch extension capability implementation and map to IntegrationDependencies.

    This function:
    1. Calls ext_client.get_extension_capability_implementation()
    2. Maps the response to ORD IntegrationDependency structure
    3. Returns list of IntegrationDependencies to inject into ORD document

    Args:
        ext_client: The extensibility client.
        capability_id: The capability ID to fetch (default: "default")
        agent: The agent dict from the ORD document to derive namespace and partOfPackage
        base_integration_deps: List of existing document-level integration dependencies
            to check against for duplicate MCP servers
        tenant: Tenant ID for the extensibility service request.

    Returns:
        List of IntegrationDependency dicts ready for ORD injection.
    """
    try:
        capability_impl = ext_client.get_extension_capability_implementation(
            capability_id=capability_id,
            skip_cache=True,
            tenant=tenant or "",
        )

        if not capability_impl:
            logger.info(
                "No extension capability implementation found for capability_id=%s",
                capability_id,
            )
            return []

        return _map_capability_to_integration_dependencies(
            capability_impl, agent, base_integration_deps
        )

    except Exception as e:
        logger.error("Failed to fetch extension capabilities: %s", e)
        raise


def add_extension_integration_dependencies(
    document: dict,
    local_tenant_id: Optional[str] = None,
    ext_client: Optional[ExtensibilityClient] = None,
) -> None:
    """Add extension integration dependencies to the ORD document.

    This method:
    1. Gets the agent from the document
    2. Fetches extension capability implementation via ext_client
    3. Injects full IntegrationDependency objects at document level
    4. Injects ordId references at agent level

    Note:
        This method should only be used for the system-instance ORD document.
        It is not intended for use with other ORD documents.

    Args:
        document: The ORD document dict (modified in-place)
        local_tenant_id: Optional tenant ID for fetching tenant-specific extensions
        ext_client: Optional extensibility client. If not provided, no extension
            dependencies will be added.
    """
    if ext_client is None:
        logger.debug(
            "No extensibility client provided, skipping extension integration dependencies"
        )
        return

    try:
        agent = document.get("agents", [{}])[0] if document.get("agents") else None

        base_integration_deps = document.get("integrationDependencies", [])

        ext_integration_deps = fetch_extension_integration_dependencies(
            ext_client=ext_client,
            agent=agent,
            base_integration_deps=base_integration_deps,
            tenant=local_tenant_id,
        )

        if not ext_integration_deps:
            return

        if "integrationDependencies" not in document:
            document["integrationDependencies"] = []
        document["integrationDependencies"].extend(ext_integration_deps)

        if agent:
            if "integrationDependencies" not in agent:
                agent["integrationDependencies"] = []
            for ext_dep in ext_integration_deps:
                ext_ord_id = ext_dep["ordId"]
                if ext_ord_id not in agent["integrationDependencies"]:
                    agent["integrationDependencies"].append(ext_ord_id)

        logger.info(
            "Added %d extension integration dependencies to instance ORD",
            len(ext_integration_deps),
        )

    except Exception as e:
        logger.warning(
            "Failed to fetch extension capabilities, continuing without them: %s",
            e,
        )
