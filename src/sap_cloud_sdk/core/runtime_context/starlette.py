"""Starlette/FastAPI context middleware and framework adapter."""

from typing import Any, List

from sap_cloud_sdk.core.runtime_context._context import (
    RequestContext,
    async_sdk_context,
)
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._registry import FrameworkAdapter, register

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
except ImportError as exc:
    raise ImportError(
        "The 'starlette' package is required to use StarletteContextMiddleware. "
        "Install it with: pip install starlette"
    ) from exc


def _merge(contexts: List[RequestContext]) -> RequestContext:
    """Merge multiple RequestContexts — first non-None value wins per field."""
    merged = RequestContext()
    for ctx in contexts:
        if merged.tenant_id is None:
            merged.tenant_id = ctx.tenant_id
        if merged.user_id is None:
            merged.user_id = ctx.user_id
        if merged.trigger_type is None:
            merged.trigger_type = ctx.trigger_type
        merged.extras.update(ctx.extras)
    return merged


class StarletteContextMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware that populates the SDK runtime context.

    Builds a :class:`~sap_cloud_sdk.core.runtime_context.RequestEnvelope` from
    each inbound request, runs all *providers* against it, and merges the results
    into a single :class:`~sap_cloud_sdk.core.runtime_context.RequestContext`
    available via :func:`~sap_cloud_sdk.core.runtime_context.get_context` for
    the duration of that request.

    First non-None value wins per field when merging. Extras are union-merged
    across all providers.
    """

    def __init__(self, app: Any, providers: List[ContextProvider]) -> None:
        super().__init__(app)
        self._providers = providers

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        envelope = RequestEnvelope(headers=dict(request.headers))
        ctx = _merge([p.extract(envelope) for p in self._providers])
        async with async_sdk_context(ctx):
            return await call_next(request)


class _StarletteContextAdapter(FrameworkAdapter):
    def _matches(self, app) -> bool:
        from starlette.applications import Starlette

        return isinstance(app, Starlette)

    def attach(self, app, providers: List[ContextProvider]) -> None:
        app.add_middleware(StarletteContextMiddleware, providers=providers)


register(_StarletteContextAdapter())
