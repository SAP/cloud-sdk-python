"""SpanProcessor that injects invoke_agent identity from a ContextVar into every span."""

from __future__ import annotations

from typing import Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

from sap_cloud_sdk.core.telemetry.telemetry import get_invoke_agent_identity


class InvokeAgentIdentitySpanProcessor(SpanProcessor):
    """Apply ``gen_ai.agent.*`` attributes stored in context to each started span.

    Values come from :func:`~sap_cloud_sdk.core.telemetry.telemetry.get_invoke_agent_identity`,
    set only while ``invoke_agent_span(..., propagate=True)`` is active. This avoids using
    W3C Baggage for in-process-only identity (review feedback: baggage size / cross-trace concerns).
    """

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        identity = get_invoke_agent_identity()
        if not identity:
            return
        for key, value in identity.items():
            span.set_attribute(key, value)

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: float = 30000) -> bool:
        return True
