"""Top-level bootstrap() entry point for the SAP Cloud SDK."""

from typing import Any

from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider


def bootstrap(app: Any, provider: ContextProvider) -> None:
    """Wire the SDK runtime context into your application framework.

    Call this once at application startup. The SDK will attach a middleware
    to *app* that populates :class:`~sap_cloud_sdk.core.runtime_context.RequestContext`
    on every inbound request using *provider*.

    After bootstrapping, any SDK module (auditlog, telemetry, etc.) can call
    :func:`~sap_cloud_sdk.core.runtime_context.get_context` to read
    tenant/user information without knowing about headers or auth providers.

    Supported frameworks (detected automatically from *app* type):
      - Starlette / FastAPI

    Args:
        app:      The application instance to attach the middleware to.
        provider: A :class:`~sap_cloud_sdk.core.runtime_context.ContextProvider`
                  that knows how to extract context from a request in this framework.

    Raises:
        TypeError: If *app* is not a recognised framework application type.

    Example::

        from starlette.applications import Starlette
        from sap_cloud_sdk import bootstrap
        from sap_cloud_sdk.core.runtime_context import IASContextProvider

        app = Starlette(...)
        bootstrap(app, provider=IASContextProvider())
    """
    _attach(app, provider)


def _attach(app: Any, provider: ContextProvider) -> None:
    """Detect framework and register the appropriate context middleware."""
    # Starlette / FastAPI — both expose add_middleware and share the same base
    try:
        from starlette.applications import Starlette
        from sap_cloud_sdk.core.runtime_context.starlette import (
            StarletteContextMiddleware,
        )

        if isinstance(app, Starlette):
            app.add_middleware(StarletteContextMiddleware, provider=provider)
            return
    except ImportError:
        pass

    raise TypeError(
        f"bootstrap() does not recognise app type {type(app)!r}. "
        "Supported frameworks: Starlette/FastAPI. "
        "For other frameworks, register the middleware manually."
    )
