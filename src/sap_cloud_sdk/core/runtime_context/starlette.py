"""Starlette/FastAPI context middleware."""

from typing import Any, List

from sap_cloud_sdk.core.runtime_context._context import (
    RuntimeContext,
    async_sdk_context,
)
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
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


class StarletteContextMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware that populates the SDK runtime context.

    Builds a :class:`~sap_cloud_sdk.core.runtime_context.RequestEnvelope` from
    each inbound request, runs all *providers* against it, and merges the results
    into a single :class:`~sap_cloud_sdk.core.runtime_context.RuntimeContext`
    available via :func:`~sap_cloud_sdk.core.runtime_context.get_context` for
    the duration of that request.

    First writer wins per key when merging across providers.
    """

    def __init__(self, app: Any, providers: List[ContextProvider]) -> None:
        super().__init__(app)
        self._providers = providers

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        envelope = RequestEnvelope(headers=dict(request.headers))
        ctx = _merge([p.extract(envelope) for p in self._providers])
        async with async_sdk_context(ctx):
            return await call_next(request)
