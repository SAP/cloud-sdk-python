"""Fragment discovery for Agent Gateway LoB flow.

Centralises all BTP Destination Service fragment operations:
- Label constants for managed-runtime fragment types
- Fragment listing by label (MCP, A2A, IAS)
- IAS fragment name lookup for auth flows
- Active integration listing for tenant context
"""

import logging
from enum import Enum
from typing import TypedDict

from sap_cloud_sdk.destination import (
    create_fragment_client,
    Label,
    ListOptions,
)
from sap_cloud_sdk.destination._models import Level

from sap_cloud_sdk.agentgateway.exceptions import MCPServerNotFoundError
from sap_cloud_sdk.core.telemetry import Module

logger = logging.getLogger(__name__)

# Shared label key for all managed-runtime fragment types
LABEL_KEY = "sap-managed-runtime-type"

# Label keys for integration metadata stored on system fragments
_LABEL_GTID = "sap-managed-runtime-gtid"
_LABEL_ORD_ID = "sap-managed-runtime-ordid"
_LABEL_SYSTEM_TYPE = "sap-managed-runtime-system-type"

_DESTINATION_INSTANCE = "default"


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


class ActiveIntegration(TypedDict):
    """Metadata for a connected backend system integration."""

    global_tenant_id: str
    system_type: str
    integration_dependency: str


def _list_active_integrations(tenant_subdomain: str) -> list[ActiveIntegration]:
    """List all active backend system integrations for the given tenant.

    Reads Destination Service instance fragments to discover active backend
    system integrations for the given tenant. Each fragment represents a
    connected backend system (e.g. SAP PCE, SAP S/4HANA).

    Retrieves integration metadata from fragment labels:
        - sap-managed-runtime-gtid: GTID of the connected partner system.
        - sap-managed-runtime-system-type: Application namespace (e.g. "sap.pce").
        - sap-managed-runtime-ordid: Sanitized ORD ID of the integration dependency.

    Args:
        tenant_subdomain: Subscriber tenant subdomain.

    Returns:
        List of ActiveIntegration dicts, each with keys:
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

    result: list[ActiveIntegration] = []
    for fragment in fragments:
        labels = {
            lbl.key: lbl.values[0] if lbl.values else None
            for lbl in client.get_fragment_labels(
                name=fragment.name,
                level=Level.SERVICE_INSTANCE,
                tenant=tenant_subdomain,
            )
        }
        gtid = labels.get(_LABEL_GTID)
        system_type = labels.get(_LABEL_SYSTEM_TYPE)
        ord_id = labels.get(_LABEL_ORD_ID)

        if not system_type:
            logger.debug(
                "Skipping fragment '%s': missing system_type label (gtid=%s, ord_id=%s)",
                fragment.name, gtid, ord_id,
            )
            continue

        result.append(
            ActiveIntegration(
                global_tenant_id=gtid,
                system_type=system_type,
                integration_dependency=ord_id,
            )
        )

    return result
