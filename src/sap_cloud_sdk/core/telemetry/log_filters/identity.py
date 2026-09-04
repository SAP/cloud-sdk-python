"""Log filter that stamps identity attributes (tenant ID, user ID) onto every log record."""

import logging

from sap_cloud_sdk.core.telemetry.constants import ATTR_SAP_TENANT_ID, ATTR_USER_ID


def _resolve_log_attributes() -> dict:
    try:
        from sap_cloud_sdk.core.runtime_context import (
            get_context,
            GLOBAL_TENANT_ID,
            USER_ID,
        )
        from sap_cloud_sdk.ias import get_auth_context

        ctx = get_context()
        claims = get_auth_context()
        candidates = {
            ATTR_SAP_TENANT_ID: ctx.get(GLOBAL_TENANT_ID)
            or (claims and claims.sap_gtid),
            ATTR_USER_ID: ctx.get(USER_ID) or (claims and claims.user_uuid),
        }
        return {k: v for k, v in candidates.items() if v}
    except Exception:
        return {}


class IdentityLogFilter(logging.Filter):
    """Stamps ``sap.tenancy.tenant_id`` and ``user.id`` onto every log record.

    Reads from the SDK runtime context first (populated by ``bootstrap()``),
    then falls back to the IAS auth context set by the Starlette middleware.
    Attributes are omitted when no identity is available (e.g. outside a request).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        for attr, value in _resolve_log_attributes().items():
            setattr(record, attr, value)
        return True
