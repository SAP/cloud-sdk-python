"""SpanProcessor that injects ContextVar-propagated attributes into every span at start time."""

import logging
from typing import Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan
from opentelemetry.trace import Span

from sap_cloud_sdk.core.telemetry.telemetry import _propagated_attrs_var

logger = logging.getLogger(__name__)


class PropagatedAttributesSpanProcessor(SpanProcessor):
    """Injects ContextVar-propagated attributes into every span at start time.

    Gives SDK context overlay attributes (set via propagate=True) visibility on
    framework-generated child spans (e.g. LangChain, LiteLLM spans created by
    Traceloop auto-instrumentation) that don't call get_propagated_attributes().

    Priority rule: propagated attrs are lowest priority — any attribute already
    set on the span at creation time wins.
    """

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        if not span.is_recording():
            return
        propagated = _propagated_attrs_var.get()
        if not propagated:
            return
        try:
            existing = getattr(span, "attributes", None) or {}
            for key, value in propagated.items():
                if key not in existing:
                    span.set_attribute(key, value)
        except Exception as exc:
            logger.debug(
                "PropagatedAttributesSpanProcessor: error injecting attributes into span %r: %s",
                getattr(span, "name", "<unknown>"),
                exc,
            )

    def on_end(self, span: ReadableSpan) -> None:
        pass
