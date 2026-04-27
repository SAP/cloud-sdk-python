"""Base interface for telemetry middlewares."""

from abc import ABC, abstractmethod

from opentelemetry.sdk.trace.export import SpanProcessor


class TelemetryMiddleware(ABC):
    """Interface for framework middlewares that enrich OpenTelemetry spans.

    Implementations are framework-specific and own everything needed to:
    - Hook into the framework's request lifecycle (register)
    - Produce span attributes from request context (span_processor)

    Example — custom Starlette middleware:

        class MyMiddleware(TelemetryMiddleware):
            def __init__(self, app):
                self._app = app
                # set up ContextVar, span processor, etc.

            def register(self):
                self._app.add_middleware(self._make_asgi_middleware())

            @property
            def span_processor(self):
                return self._span_processor
    """

    @property
    @abstractmethod
    def span_processor(self) -> SpanProcessor:
        """OTel SpanProcessor registered by auto_instrument on the tracer provider."""

    @abstractmethod
    def register(self) -> None:
        """Hook the middleware into the framework.

        Called by auto_instrument before span processors are registered.
        """
