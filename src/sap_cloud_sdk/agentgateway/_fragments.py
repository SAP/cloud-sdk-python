"""Fragment discovery for Agent Gateway LoB flow.

Centralises all BTP Destination Service fragment operations:
- Label constants for managed-runtime fragment types
- Fragment listing by label (MCP, A2A, IAS)
- IAS fragment name lookup for auth flows
- Active integration listing for tenant context
"""

import logging
from enum import Enum
from typing import Optional

from sap_cloud_sdk.destination import (
    create_fragment_client,
    Label,
    ListOptions,
)

from sap_cloud_sdk.agentgateway.exceptions import MCPServerNotFoundError
from sap_cloud_sdk.core.telemetry import Module

logger = logging.getLogger(__name__)

# Shared label key for all managed-runtime fragment types
LABEL_KEY = "sap-managed-runtime-type"

_DESTINATION_INSTANCE = "default"

# URL mode path segments used by system integration fragments
_INTEGRATION_URL_MODES = ("mcp", "a2a")


class FragmentLabel(str, Enum):
    """Label values for the sap-managed-runtime-type fragment label key."""

    MCP = "agw.mcp.server"
    A2A = "agw.a2a.server"
    IAS = "subscriber.ias"
    IAS_USER = "subscriber.ias.user"


def _list_fragments_by_label(label: FragmentLabel, tenant_subdomain: str) -> list:
    client = create_fragment_client(
        instance=_DESTINATION_INSTANCE,
        _telemetry_source=Module.AGENTGATEWAY,
    )
    return client.list_instance_fragments(
        filter=ListOptions(filter_labels=[Label(key=LABEL_KEY, values=[label.value])]),
        tenant=tenant_subdomain,
    )


def list_mcp_fragments(tenant_subdomain: str) -> list:
    """List destination fragments with MCP server label.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        List of fragments with sap-managed-runtime-type=agw.mcp.server label.
    """
    logger.debug("Fetching MCP fragments for tenant '%s'", tenant_subdomain)
    return _list_fragments_by_label(FragmentLabel.MCP, tenant_subdomain)


def list_a2a_fragments(tenant_subdomain: str) -> list:
    """List destination fragments with A2A label.

    Args:
        tenant_subdomain: Tenant subdomain for multi-tenant lookup.

    Returns:
        List of fragments with sap-managed-runtime-type=agw.a2a.server label.
    """
    logger.debug("Fetching A2A fragments for tenant '%s'", tenant_subdomain)
    return _list_fragments_by_label(FragmentLabel.A2A, tenant_subdomain)


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
    fragments = _list_fragments_by_label(FragmentLabel.IAS, tenant_subdomain)
    if not fragments:
        raise MCPServerNotFoundError(
            f"No IAS fragment found (label {LABEL_KEY}={FragmentLabel.IAS.value}) "
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
    fragments = _list_fragments_by_label(FragmentLabel.IAS_USER, tenant_subdomain)
    if not fragments:
        raise MCPServerNotFoundError(
            f"No IAS user fragment found (label {LABEL_KEY}={FragmentLabel.IAS_USER.value}) "
            f"for tenant '{tenant_subdomain}'"
        )
    return fragments[0].name


def list_active_integrations(tenant_subdomain: str) -> list[dict]:
    """List all active backend system integrations for the given tenant.

    Reads Destination Service instance fragments to discover active backend
    system integrations for the given tenant. Each fragment represents a
    connected backend system (e.g. SAP PCE, SAP S/4HANA).

    Extracts integration details from the fragment URL, which always has the form:
        {agw_base_url}/v1/mcp/{ord_id}/{gtid}   (MCP integrations)
        {agw_base_url}/v1/a2a/{ord_id}/{gtid}   (A2A integrations)

    Args:
        tenant_subdomain: Subscriber tenant subdomain.

    Returns:
        List of dicts, each with keys:
            - global_tenant_id: GTID of the connected partner system.
            - system_type: Application namespace of the partner (e.g. "sap.pce").
            - integration_dependency: ORD ID of the integration dependency fulfilled.
        Returns empty list if no active integrations exist.
    """
    client = create_fragment_client(
        instance=_DESTINATION_INSTANCE,
        _telemetry_source=Module.AGENTGATEWAY,
    )
    fragments = client.list_instance_fragments(
        filter=ListOptions(
            filter_labels=[
                Label(
                    key=LABEL_KEY,
                    values=[FragmentLabel.MCP.value, FragmentLabel.A2A.value],
                )
            ]
        ),
        tenant=tenant_subdomain,
    )

    result = []
    for fragment in fragments:
        url = fragment.properties.get("URL", "")
        entry = _parse_integration_from_url(url)
        if entry is not None:
            result.append(entry)
    return result


def _parse_integration_from_url(url: str) -> Optional[dict]:
    """Extract integration metadata from a system fragment URL.

    Fragment URLs have the form:
        {base}/v1/{mode}/{ord_id}/{gtid}
    where mode is "mcp" or "a2a", ord_id may contain colons and slashes,
    and gtid is the last path segment.

    Args:
        url: The fragment URL property value.

    Returns:
        Dict with global_tenant_id, system_type, integration_dependency,
        or None if the URL does not match the expected pattern.
    """
    parts = url.rstrip("/").split("/")

    mode_idx = None
    for i, part in enumerate(parts):
        if i > 0 and parts[i - 1] == "v1" and part in _INTEGRATION_URL_MODES:
            mode_idx = i
            break

    if mode_idx is None or mode_idx + 2 > len(parts) - 1:
        logger.debug("Skipping fragment with unexpected URL pattern: %s", url)
        return None

    gtid = parts[-1]
    ord_id = "/".join(parts[mode_idx + 1 : -1])
    system_type = ord_id.split(":")[0]

    if not gtid or not ord_id:
        logger.debug("Skipping fragment with empty gtid or ord_id in URL: %s", url)
        return None

    return {
        "global_tenant_id": gtid,
        "system_type": system_type,
        "integration_dependency": ord_id,
    }
