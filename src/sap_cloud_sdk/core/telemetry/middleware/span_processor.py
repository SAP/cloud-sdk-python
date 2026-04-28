"""MiddlewareSpanProcessor: stamps middleware-extracted attributes onto every span."""

from __future__ import annotations

import logging
from typing import List, Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

from sap_cloud_sdk.core.telemetry.middleware.base import TelemetryMiddleware

logger = logging.getLogger(__name__)


class MiddlewareSpanProcessor(SpanProcessor):
    """SpanProcessor that stamps attributes from TelemetryMiddleware instances onto spans.

    Registered automatically by ``auto_instrument()`` when the ``middlewares``
    argument is non-empty.
    """

    def __init__(self, middlewares: List[TelemetryMiddleware]) -> None:
        """
        Args:
            middlewares: Middleware instances whose per-request attributes should
                         be stamped onto every span at start time.
        """
        self._middlewares = middlewares

    def on_start(
        self,
        span: Span,
        parent_context: Optional[Context] = None,
    ) -> None:
        if not span.is_recording():
            return
        for middleware in self._middlewares:
            try:
                for key, value in middleware.get_attributes().items():
                    span.set_attribute(key, value)
            except Exception as exc:
                logger.debug(
                    "MiddlewareSpanProcessor: error reading attributes from %r: %s",
                    middleware,
                    exc,
                )

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
