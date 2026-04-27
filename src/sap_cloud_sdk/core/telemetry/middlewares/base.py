"""Base class for header-to-span-attribute middlewares."""

from abc import ABC, abstractmethod
from contextvars import ContextVar
from typing import Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span
from opentelemetry.sdk.trace.export import SpanProcessor


class HeaderSpanMiddleware(ABC):
    """Base class for header-to-span-attribute middlewares.

    Subclass and set `header_name` and `span_attribute`. Optionally override
    `transform_value` to mutate the header value before it is written to the span.

    The base class provides:
    - `asgi_middleware_class`: an ASGI middleware to mount on your app that
      captures the header from each request into a ContextVar.
    - `span_processor`: an OTel SpanProcessor to pass to auto_instrument that
      reads the ContextVar and writes the attribute on every new span.

    Example:
        class MyMiddleware(HeaderSpanMiddleware):
            header_name = "x-my-header"
            span_attribute = "my.attribute"

        middleware = MyMiddleware()
        app.add_middleware(middleware.asgi_middleware_class)
        auto_instrument(middlewares=[middleware])
    """

    def __init__(self) -> None:
        self._context_var: ContextVar[Optional[str]] = ContextVar(
            f"_header_{self.header_name}", default=None
        )
        self.asgi_middleware_class = self._make_asgi_middleware()
        self.span_processor = self._make_span_processor()

    def register(self) -> None:
        """Register the middleware with the framework. Called by auto_instrument.

        Override in framework-specific subclasses to mount the ASGI/WSGI
        middleware on the app passed to the constructor.
        """

    @property
    @abstractmethod
    def header_name(self) -> str:
        """HTTP header name to capture (lowercase, e.g. 'x-origin')."""

    @property
    @abstractmethod
    def span_attribute(self) -> str:
        """OTel span attribute key (e.g. 'a2a.origin')."""

    def transform_value(self, value: str) -> str:
        """Override to transform the header value before writing it to the span."""
        return value

    def _make_asgi_middleware(self) -> type:
        header_bytes = self.header_name.encode()
        context_var = self._context_var

        class _ASGIMiddleware:
            def __init__(self_, app) -> None:  # noqa: N805
                self_.app = app

            async def __call__(self_, scope, receive, send) -> None:  # noqa: N805
                if scope["type"] == "http":
                    headers = dict(scope.get("headers", []))
                    raw = headers.get(header_bytes)
                    token = context_var.set(raw.decode() if raw is not None else None)
                    try:
                        await self_.app(scope, receive, send)
                    finally:
                        context_var.reset(token)
                else:
                    await self_.app(scope, receive, send)

        return _ASGIMiddleware

    def _make_span_processor(self) -> SpanProcessor:
        context_var = self._context_var
        span_attribute = self.span_attribute
        transform = self.transform_value

        class _HeaderSpanProcessor(SpanProcessor):
            def on_start(
                self_, span: Span, parent_context: Optional[Context] = None  # noqa: N805
            ) -> None:
                value = context_var.get()
                if value is not None and span.is_recording():
                    span.set_attribute(span_attribute, transform(value))

            def on_end(self_, span: ReadableSpan) -> None:  # noqa: N805
                pass

            def shutdown(self_) -> None:  # noqa: N805
                pass

            def force_flush(self_, timeout_millis: int = 30000) -> bool:  # noqa: N805
                return True

        return _HeaderSpanProcessor()
