"""Audit log helper for custom events.

Provides managed client creation and a ``ZzzCustomEvent`` send pattern —
the SAP Audit Log v2 event type for application-defined audit events, 
which are not covered by the standard catalog.

For standard catalog events (``DataAccess``, ``ConfigurationChange``,
``UserLoginSuccess``, etc.), construct the protobuf directly and call
``AuditClient.send()``.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

import sap_cloud_sdk.core.auditlog_ng as auditlog_ng
from sap_cloud_sdk.core.auditlog_ng.client import AuditClient
from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import (
    auditevent_pb2 as pb,
)
from sap_cloud_sdk.core.telemetry import Module, get_tenant_id

logger = logging.getLogger(__name__)


class AuditLogMode(Enum):
    """Controls how audit logging failures are handled.

    Attributes:
        DISABLED: Audit logging is skipped entirely.
        BEST_EFFORT: Failures are logged at WARNING level but never raised.
            This is the default.
        STRICT: Failures raise an exception, blocking the operation.
    """

    DISABLED = "disabled"
    BEST_EFFORT = "best_effort"
    STRICT = "strict"


def _emit_custom_event(
    audit_client: AuditClient,
    tenant_id: str,
    event_name: str,
    payload: dict,
    user_id: str | None = None,
) -> None:
    """Build and send a ZzzCustomEvent to the audit log service.

    Args:
        audit_client: Initialized AuditClient instance.
        tenant_id: Tenant UUID stamped on the event.
        event_name: Event identifier (e.g. ``"MCP_TOOL_INVOKED"``).
        payload: Arbitrary key/value pairs serialized into the custom struct.
            ``event_name`` is always included automatically.
        user_id: Optional user initiator ID stamped on the event.
    """
    common = pb.Common()
    common.timestamp.FromDatetime(datetime.now(timezone.utc))
    common.tenant_id = tenant_id
    common.app_context["event_name"] = event_name
    if user_id:
        common.user_initiator_id = user_id

    event = pb.ZzzCustomEvent()
    event.common.CopyFrom(common)
    event.custom.struct_value.update({"event_name": event_name, **payload})
    audit_client.send(event)


def _resolve_tenant(tenant_subdomain: str | Callable[[], str] | None) -> str | None:
    if isinstance(tenant_subdomain, str):
        return tenant_subdomain
    if callable(tenant_subdomain):
        return tenant_subdomain()
    return None


def create_audit_client(
    tenant_subdomain: str | Callable[[], str] | None,
    module: Module,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> AuditClient | None:
    """Create an audit client from a LoB destination.

    Args:
        tenant_subdomain: Tenant subdomain string or callable returning one.
        module: Telemetry source module identifier.
        mode: Controls failure handling. Returns None when DISABLED or when
            tenant is not resolvable.

    Returns:
        Initialized AuditClient, or None on failure / when disabled.
    """
    if mode is AuditLogMode.DISABLED:
        return None
    resolved = _resolve_tenant(tenant_subdomain)
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
        # BEST_EFFORT: suppress the error and warn instead of propagating
        logger.warning(
            "Failed to create audit client — audit events will not be recorded",
            exc_info=True,
        )
        return None


def send_event(
    audit_client: AuditClient | None,
    event_name: str,
    payload: dict,
    user_id: str | None = None,
    mode: AuditLogMode = AuditLogMode.BEST_EFFORT,
) -> None:
    """Send a ZzzCustomEvent to the audit log service.

    Resolves the tenant ID via ``get_tenant_id()`` and applies ``AuditLogMode``
    semantics around the send. No-op when disabled, client is None, or tenant
    is not resolvable.

    Args:
        audit_client: Initialized AuditClient, or None to skip.
        event_name: Event identifier stamped on the event (e.g. ``"MCP_TOOL_INVOKED"``).
        payload: Arbitrary key/value pairs included in the custom struct.
        user_id: Optional user initiator ID.
        mode: Controls failure handling.
    """
    if mode is AuditLogMode.DISABLED:
        return
    tenant_id = get_tenant_id()
    if audit_client is None or not tenant_id:
        return
    try:
        _emit_custom_event(audit_client, tenant_id, event_name, payload, user_id)
    except Exception:
        if mode is AuditLogMode.STRICT:
            raise
        # BEST_EFFORT: supress the error and warn instead of propagating
        logger.warning("Failed to send audit event", exc_info=True)
