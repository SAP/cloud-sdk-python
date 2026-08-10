"""SpanProcessor that injects SDK runtime context identity fields into every span at start time."""

import logging
from typing import Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan
from opentelemetry.trace import Span

from sap_cloud_sdk.core.runtime_context import APP_TENANT_ID, GLOBAL_TENANT_ID, USER_ID
from sap_cloud_sdk.core.telemetry.constants import (
    ATTR_SAP_TENANT_ID,
    ATTR_USER_ID,
)

logger = logging.getLogger(__name__)

_CONTEXT_TO_SPAN_ATTR = {
    APP_TENANT_ID: ATTR_SAP_TENANT_ID,
    GLOBAL_TENANT_ID: ATTR_SAP_TENANT_ID,
    USER_ID: ATTR_USER_ID,
}


class RuntimeContextSpanProcessor(SpanProcessor):
    """Injects tenant and user identity from the SDK runtime context into every span.

    Reads APP_TENANT_ID, GLOBAL_TENANT_ID, and USER_ID from the runtime context
    populated by bootstrap() providers (e.g. IASContextProvider) and stamps them
    as span attributes on every span at start time.
    """

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        if not span.is_recording():
            return
        try:
            from sap_cloud_sdk.core.runtime_context import get_context

            ctx = get_context()
            for context_key, span_attr in _CONTEXT_TO_SPAN_ATTR.items():
                if value := ctx.get(context_key):
                    span.set_attribute(span_attr, value)
        except Exception as exc:
            logger.debug(
                "RuntimeContextSpanProcessor: error injecting context into span %r: %s",
                getattr(span, "name", "<unknown>"),
                exc,
            )

    def on_end(self, span: ReadableSpan) -> None:
        pass
