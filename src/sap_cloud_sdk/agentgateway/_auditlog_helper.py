"""Audit log helpers for the Agent Gateway client."""

import logging
from datetime import datetime, timezone
from typing import Callable

import sap_cloud_sdk.core.auditlog_ng as auditlog_ng
from sap_cloud_sdk.agentgateway.config import AuditLogMode
from sap_cloud_sdk.core.auditlog_ng import AuditClient
from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import (
    auditevent_pb2 as pb,
)
from sap_cloud_sdk.core.telemetry import Module, get_tenant_id

logger = logging.getLogger(__name__)


def create_audit_client(
    tenant_subdomain: str | Callable[[], str] | None,
    module: Module,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> AuditClient | None:
    """Create an audit client from a LoB destination. Returns None on failure."""
    if mode is AuditLogMode.DISABLED:
        return None
    resolved = tenant_subdomain() if callable(tenant_subdomain) else tenant_subdomain
    if not resolved:
        return None
    try:
        return auditlog_ng.create_client(
            tenant=resolved,
            _telemetry_source=module,
        )
    except Exception:
        if mode is AuditLogMode.STRICT:
            raise
        # BEST_EFFORT: suppress and warn — audit failure must never break the main flow
        logger.warning("Failed to create audit client — audit events will not be recorded", exc_info=True)
        return None


def send_audit_event(
    audit_client: AuditClient | None,
    object_id: str,
    user_id: str | None = None,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> None:
    """Send a DataAccess audit event."""
    if mode is AuditLogMode.DISABLED:
        return
    tenant_id = get_tenant_id()
    if audit_client is None or not tenant_id:
        return
    try:
        event = pb.DataAccess()
        event.common.timestamp.FromDatetime(datetime.now(timezone.utc))
        event.common.tenant_id = tenant_id
        if user_id:
            event.common.user_initiator_id = user_id
        event.channel_type = "MCP"
        event.channel_id = "agent-gateway"
        event.object_type = "mcp-tool"
        event.object_id = object_id
        audit_client.send(event)
    except Exception:
        if mode is AuditLogMode.STRICT:
            raise
        # BEST_EFFORT: suppress and warn — audit failure must never break the main flow
        logger.warning("Failed to send audit event", exc_info=True)
