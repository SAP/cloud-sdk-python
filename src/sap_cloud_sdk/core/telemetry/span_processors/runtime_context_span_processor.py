"""SpanProcessor that stamps runtime context attributes onto every span at start time."""

import logging
from typing import Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.trace import Span

from sap_cloud_sdk.core.runtime_context._context import get_context
from sap_cloud_sdk.core.runtime_context.providers._ias import GLOBAL_TENANT_ID, USER_ID
from sap_cloud_sdk.core.runtime_context._keys import TRIGGER_TYPE
from sap_cloud_sdk.core.telemetry.constants import (
    ATTR_SAP_TENANT_ID,
    ATTR_SAP_TRIGGER_TYPE,
    ATTR_USER_ID,
)

logger = logging.getLogger(__name__)

_CONTEXT_KEY_TO_ATTR = {
    GLOBAL_TENANT_ID: ATTR_SAP_TENANT_ID,
    USER_ID: ATTR_USER_ID,
    TRIGGER_TYPE: ATTR_SAP_TRIGGER_TYPE,
}


class RuntimeContextSpanProcessor(SpanProcessor):
    """Stamps runtime context values as span attributes on every span at start time.

    Reads the current :func:`~sap_cloud_sdk.core.runtime_context.get_context`
    and maps the following keys to span attributes:

      - ``ias.sap_gtid``   → ``sap.tenancy.tenant_id``
      - ``ias.user_uuid``  → ``user.id``
      - ``trigger_type``   → ``sap.ai.agent.trigger.type``

    Only attributes not already set on the span are written (existing values win).
    No-ops outside a request context (i.e. when ``get_context()`` returns empty).
    """

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        if not span.is_recording():
            return
        ctx = get_context()
        try:
            existing = getattr(span, "attributes", None) or {}
            for key, attr_name in _CONTEXT_KEY_TO_ATTR.items():
                value = ctx.get(key)
                if value is not None and attr_name not in existing:
                    span.set_attribute(attr_name, value)
        except Exception as exc:
            logger.debug(
                "RuntimeContextSpanProcessor: error injecting attributes into span %r: %s",
                getattr(span, "name", "<unknown>"),
                exc,
            )

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
