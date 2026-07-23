"""Starlette/FastAPI framework adapter."""

from typing import List

from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._registry import FrameworkAdapter, register


class _StarletteContextAdapter(FrameworkAdapter):
    def _matches(self, app) -> bool:
        from starlette.applications import Starlette

        return isinstance(app, Starlette)

    def attach(self, app, providers: List[ContextProvider]) -> None:
        from sap_cloud_sdk.core.runtime_context.starlette import (
            StarletteContextMiddleware,
        )

        app.add_middleware(StarletteContextMiddleware, providers=providers)


register(_StarletteContextAdapter())
