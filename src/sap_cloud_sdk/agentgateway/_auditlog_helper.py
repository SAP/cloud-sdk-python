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

MCP_TOOL_INVOKED = "MCP_TOOL_INVOKED"
MCP_TOOL_COMPLETED = "MCP_TOOL_COMPLETED"
MCP_TOOL_FAILED = "MCP_TOOL_FAILED"


def create_audit_client(
    tenant_subdomain: str | Callable[[], str] | None,
    module: Module,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> AuditClient | None:
    """Create an audit client from a LoB destination. Returns None on failure."""
    if mode is AuditLogMode.DISABLED:
        return None
    if isinstance(tenant_subdomain, str):
        resolved: str | None = tenant_subdomain
    elif tenant_subdomain is not None:
        resolved = tenant_subdomain()
    else:
        resolved = None
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
        # BEST_EFFORT: suppress and warn — audit failure does not break the main agw flow
        logger.warning(
            "Failed to create audit client — audit events will not be recorded",
            exc_info=True,
        )
        return None


def _build_custom_event(
    event_name: str,
    tool_name: str,
    tenant_id: str,
    user_id: str | None,
    extra: dict | None = None,
) -> pb.ZzzCustomEvent:
    common = pb.Common()
    common.timestamp.FromDatetime(datetime.now(timezone.utc))
    common.tenant_id = tenant_id
    common.app_context["event_name"] = event_name
    if user_id:
        common.user_initiator_id = user_id

    payload: dict = {"event_name": event_name, "tool": tool_name}
    if extra:
        payload.update(extra)

    event = pb.ZzzCustomEvent()
    event.common.CopyFrom(common)
    event.custom.struct_value.update(payload)
    return event


def _send(
    audit_client: AuditClient | None,
    event_name: str,
    tool_name: str,
    user_id: str | None,
    mode: AuditLogMode,
    extra: dict | None = None,
) -> None:
    if mode is AuditLogMode.DISABLED:
        return
    tenant_id = get_tenant_id()
    if audit_client is None or not tenant_id:
        return
    event = _build_custom_event(event_name, tool_name, tenant_id, user_id, extra)
    try:
        audit_client.send(event)
    except Exception:
        if mode is AuditLogMode.STRICT:
            raise
        # BEST_EFFORT: suppress and warn — audit failure does not break the main agw flow
        logger.warning("Failed to send audit event", exc_info=True)


def send_audit_event_invoked(
    audit_client: AuditClient | None,
    tool_name: str,
    user_id: str | None = None,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> None:
    """Emit MCP_TOOL_INVOKED before the tool call starts."""
    _send(audit_client, MCP_TOOL_INVOKED, tool_name, user_id, mode)


def send_audit_event_completed(
    audit_client: AuditClient | None,
    tool_name: str,
    user_id: str | None = None,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> None:
    """Emit MCP_TOOL_COMPLETED after the tool call succeeds."""
    _send(audit_client, MCP_TOOL_COMPLETED, tool_name, user_id, mode)


def send_audit_event_failed(
    audit_client: AuditClient | None,
    tool_name: str,
    error_type: str,
    user_id: str | None = None,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> None:
    """Emit MCP_TOOL_FAILED when the tool call raises an exception."""
    _send(audit_client, MCP_TOOL_FAILED, tool_name, user_id, mode, extra={"error_type": error_type})
