"""Starlette/FastAPI telemetry middlewares."""

from contextvars import ContextVar
from typing import Any, Callable, Optional

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span
from opentelemetry.sdk.trace.export import SpanProcessor

from sap_cloud_sdk.core.telemetry.middlewares.base import TelemetryMiddleware


class _ASGIHeaderMiddleware:
    def __init__(
        self,
        app: Any,
        context_var: ContextVar,
        extract: Callable[[dict], Optional[dict]],
    ) -> None:
        self.app = app
        self._context_var = context_var
        self._extract = extract

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            token = self._context_var.set(self._extract(headers))
            try:
                await self.app(scope, receive, send)
            finally:
                self._context_var.reset(token)
        else:
            await self.app(scope, receive, send)


class _AttrsSpanProcessor(SpanProcessor):
    def __init__(self, context_var: ContextVar) -> None:
        self._context_var = context_var

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        attrs = self._context_var.get()
        if attrs and span.is_recording():
            for key, value in attrs.items():
                span.set_attribute(key, value)

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class A2AStarletteMiddleware(TelemetryMiddleware):
    """Captures A2A request headers and stamps them as span attributes.

    Pass the Starlette/FastAPI app to the constructor. auto_instrument will call
    register() which mounts the ASGI middleware on the app automatically:

        auto_instrument(middlewares=[A2AStarletteMiddleware(app)])

    Add or remove headers by editing _HEADERS: each entry maps a request header
    (bytes) to the span attribute name it should be written to.
    """

    _HEADERS: dict[bytes, str] = {
        b"x-origin": "a2a.origin",
    }

    def __init__(self, app: Any) -> None:
        self._app = app
        self._context_var: ContextVar[Optional[dict]] = ContextVar(
            "_a2a_starlette_attrs", default=None
        )
        self._span_processor = _AttrsSpanProcessor(self._context_var)

    @property
    def span_processor(self) -> SpanProcessor:
        return self._span_processor

    def register(self) -> None:
        self._app.add_middleware(
            _ASGIHeaderMiddleware,
            context_var=self._context_var,
            extract=self._extract,
        )

    def _extract(self, headers: dict) -> Optional[dict]:
        attrs = {
            attr: headers[header].decode()
            for header, attr in self._HEADERS.items()
            if header in headers
        }
        return attrs or None
