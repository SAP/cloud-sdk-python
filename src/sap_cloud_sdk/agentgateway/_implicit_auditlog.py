"""Audit log helpers for the Agent Gateway client."""

from sap_cloud_sdk.core.auditlog_ng import AuditClient
from sap_cloud_sdk.core.auditlog_ng.helper import (
    AuditLogMode,
    create_audit_client,
    send_event,
)

__all__ = [
    "AuditLogMode",
    "create_audit_client",
    "MCP_TOOL_INVOKED",
    "MCP_TOOL_COMPLETED",
    "MCP_TOOL_FAILED",
    "send_audit_event_invoked",
    "send_audit_event_completed",
    "send_audit_event_failed",
]

MCP_TOOL_INVOKED = "MCP_TOOL_INVOKED"
MCP_TOOL_COMPLETED = "MCP_TOOL_COMPLETED"
MCP_TOOL_FAILED = "MCP_TOOL_FAILED"


def send_audit_event_invoked(
    audit_client: AuditClient | None,
    tool_name: str,
    user_id: str | None = None,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> None:
    """Emit MCP_TOOL_INVOKED before the tool call starts."""
    send_event(audit_client, MCP_TOOL_INVOKED, {"tool": tool_name}, user_id, mode)


def send_audit_event_completed(
    audit_client: AuditClient | None,
    tool_name: str,
    user_id: str | None = None,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> None:
    """Emit MCP_TOOL_COMPLETED after the tool call succeeds."""
    send_event(audit_client, MCP_TOOL_COMPLETED, {"tool": tool_name}, user_id, mode)


def send_audit_event_failed(
    audit_client: AuditClient | None,
    tool_name: str,
    error_type: str,
    user_id: str | None = None,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> None:
    """Emit MCP_TOOL_FAILED when the tool call raises an exception."""
    send_event(
        audit_client,
        MCP_TOOL_FAILED,
        {"tool": tool_name, "error_type": error_type},
        user_id,
        mode,
    )
