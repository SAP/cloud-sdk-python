"""Internal audit log helpers for extension lifecycle events.

All functions emit DataAccess events via sap_cloud_sdk.core.auditlog_ng.
They are fire-and-forget: failures are logged and silently swallowed so
audit errors never interrupt the agent request path.

These functions are called internally by ExtensibilityClient; agents do not
call them directly.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000000"


def _get_tenant_id(tenant_id: str) -> str:
    if tenant_id:
        return tenant_id
    provider = os.environ.get("SAP_CLD_SUBACCOUNT_ID", "")
    if provider:
        return provider
    logger.warning(
        "audit: no tenant_id and no SAP_CLD_SUBACCOUNT_ID — "
        "stamping zero-UUID; events may not appear in ALS viewer"
    )
    return _DEFAULT_TENANT_ID


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_client(tenant_subdomain: str, channel_id: str, service_name: str) -> Any:
    from sap_cloud_sdk.core.auditlog_ng import create_client as _create

    fragment_name = f"AuditLogV3_Fragment_{tenant_subdomain}"
    return _create(
        tenant=tenant_subdomain,
        destination_name="AuditLogV3_Destination",
        destination_instance="default",
        fragment_name=fragment_name,
        service_name=service_name,
        batch=True,
    )


def _send(client: Any, event: Any) -> None:
    try:
        client.send(event)
    finally:
        client.close()


async def _emit_hook_executed(
    *,
    phase: str,
    tenant_subdomain: str,
    tenant_id: str,
    user_id: str,
    hook_name: str,
    capability_id: str,
    channel_id: str,
    service_name: str,
) -> None:
    if not tenant_subdomain or not channel_id:
        return
    try:
        from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import (
            auditevent_pb2 as pb,
        )

        client = _make_client(tenant_subdomain, channel_id, service_name)
        event = pb.DataAccess()
        event.common.timestamp.FromDatetime(_now())
        event.common.app_id = service_name
        event.common.user_initiator_id = user_id or "unknown"
        event.common.tenant_id = _get_tenant_id(tenant_id)
        event.channel_type = "API"
        event.channel_id = channel_id
        event.object_type = "extension_hook"
        event.object_id = hook_name
        event.attribute = f"phase={phase} capability={capability_id}"
        _send(client, event)
    except Exception:
        logger.warning("audit hook_executed (%s) failed", phase, exc_info=True)


async def _emit_hook_short_circuit(
    *,
    tenant_subdomain: str,
    tenant_id: str,
    user_id: str,
    hook_name: str,
    capability_id: str,
    reason: str,
    channel_id: str,
    service_name: str,
) -> None:
    if not tenant_subdomain or not channel_id:
        return
    try:
        from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import (
            auditevent_pb2 as pb,
        )

        client = _make_client(tenant_subdomain, channel_id, service_name)
        event = pb.DataAccess()
        event.common.timestamp.FromDatetime(_now())
        event.common.app_id = service_name
        event.common.user_initiator_id = user_id or "unknown"
        event.common.tenant_id = _get_tenant_id(tenant_id)
        event.channel_type = "API"
        event.channel_id = channel_id
        event.object_type = "extension_hook"
        event.object_id = hook_name
        event.attribute = f"phase=pre action=short_circuit capability={capability_id} reason={reason[:200]}"
        _send(client, event)
    except Exception:
        logger.warning("audit hook_short_circuit failed", exc_info=True)


async def _emit_instruction_applied(
    *,
    tenant_subdomain: str,
    tenant_id: str,
    user_id: str,
    context_id: str,
    capability_id: str,
    channel_id: str,
    service_name: str,
) -> None:
    if not tenant_subdomain or not channel_id:
        return
    try:
        from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import (
            auditevent_pb2 as pb,
        )

        client = _make_client(tenant_subdomain, channel_id, service_name)
        event = pb.DataAccess()
        event.common.timestamp.FromDatetime(_now())
        event.common.app_id = service_name
        event.common.user_initiator_id = user_id or "unknown"
        event.common.tenant_id = _get_tenant_id(tenant_id)
        event.channel_type = "API"
        event.channel_id = channel_id
        event.object_type = "extension_instruction"
        event.object_id = capability_id or "default"
        event.attribute = f"context={context_id}"
        _send(client, event)
    except Exception:
        logger.warning("audit instruction_applied failed", exc_info=True)
