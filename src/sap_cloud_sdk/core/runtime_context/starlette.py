"""Starlette/FastAPI context middleware."""

from typing import Any

from sap_cloud_sdk.core.runtime_context._context import async_sdk_context
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


class StarletteContextMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware that populates the SDK runtime context.

    Runs *provider*.extract() on every inbound request and makes the result
    available via :func:`~sap_cloud_sdk.core.runtime_context.get_context`
    for the duration of that request.

    Usage::

        from starlette.applications import Starlette
        from sap_cloud_sdk import bootstrap

        app = Starlette(...)
        bootstrap(app)

    Or manually::

        from sap_cloud_sdk.core.runtime_context.starlette import StarletteContextMiddleware
        from sap_cloud_sdk.core.runtime_context import IASContextProvider

        app.add_middleware(StarletteContextMiddleware, provider=IASContextProvider())
    """

    def __init__(self, app: Any, provider: ContextProvider) -> None:
        super().__init__(app)
        self._provider = provider

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        ctx = self._provider.extract(request)
        async with async_sdk_context(ctx):
            return await call_next(request)
