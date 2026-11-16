"""Starlette/FastAPI context middleware."""

from typing import Any, Callable, List

from sap_cloud_sdk.core.runtime_context._context import (
    RuntimeContext,
    async_sdk_context,
)
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider

try:
    from starlette.datastructures import Headers
except ImportError as exc:
    raise ImportError(
        "The 'starlette' package is required to use StarletteContextMiddleware. "
        "Install it with: pip install starlette"
    ) from exc


def _merge(contexts: List[RuntimeContext]) -> RuntimeContext:
    """Merge multiple RuntimeContexts — first writer wins per key."""
    merged: dict = {}
    for ctx in contexts:
        for key, value in ctx._raw().items():
            merged.setdefault(key, value)
    return RuntimeContext(merged)


class StarletteContextMiddleware:
    """Starlette/FastAPI middleware that populates the SDK runtime context.

    Implemented as a pure ASGI middleware (no dependency on ``BaseHTTPMiddleware``),
    so it is compatible with both Starlette and FastAPI via ``app.add_middleware()``.

    Builds a :class:`~sap_cloud_sdk.core.runtime_context.RequestEnvelope` from
    each inbound request, runs all *providers* against it, and merges the results
    into a single :class:`~sap_cloud_sdk.core.runtime_context.RuntimeContext`
    available via :func:`~sap_cloud_sdk.core.runtime_context.get_context` for
    the duration of that request.

    Non-HTTP scopes (lifespan, websocket) are forwarded without modification.
    First writer wins per key when merging across providers.
    """

    def __init__(self, app: Any, providers: List[ContextProvider]) -> None:
        self.app = app
        self._providers = providers

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(raw=scope["headers"])
        envelope = RequestEnvelope(headers=dict(headers))
        ctx = _merge([p.extract(envelope) for p in self._providers])
        async with async_sdk_context(ctx):
            await self.app(scope, receive, send)
