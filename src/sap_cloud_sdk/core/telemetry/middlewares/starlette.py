"""Starlette/FastAPI header-to-span-attribute middlewares."""

from typing import Any

from sap_cloud_sdk.core.telemetry.middlewares.base import HeaderSpanMiddleware


class A2AStarletteMiddleware(HeaderSpanMiddleware):
    """Captures the 'x-origin' header from A2A requests and stamps it on spans.

    Pass the Starlette/FastAPI app to the constructor. auto_instrument will call
    register() which mounts the ASGI middleware on the app automatically:

        auto_instrument(middlewares=[A2AStarletteMiddleware(app)])

    Every span created while handling a request that carries the 'x-origin'
    header will have the attribute 'a2a.origin' set to its value.
    """

    def __init__(self, app: Any) -> None:
        self._app = app
        super().__init__()

    def register(self) -> None:
        self._app.add_middleware(self.asgi_middleware_class)

    @property
    def header_name(self) -> str:
        return "x-origin"

    @property
    def span_attribute(self) -> str:
        return "a2a.origin"
