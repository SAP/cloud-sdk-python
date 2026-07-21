"""Top-level bootstrap() entry point for the SAP Cloud SDK."""

from typing import Any, List, Optional

from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider


def bootstrap(app: Any, providers: Optional[List[ContextProvider]] = None) -> None:
    """Wire the SDK runtime context into your application framework.

    Call this once at application startup. The SDK will attach a middleware
    to *app* that populates :class:`~sap_cloud_sdk.core.runtime_context.RequestContext`
    on every inbound request by running all *providers* against it and merging
    the results.

    After bootstrapping, any SDK module (auditlog, telemetry, etc.) can call
    :func:`~sap_cloud_sdk.core.runtime_context.get_context` to read
    tenant/user information without knowing about headers or auth providers.

    Supported frameworks (detected automatically from *app* type):
      - Starlette / FastAPI

    Args:
        app:       The application instance to attach the middleware to.
        providers: One or more :class:`~sap_cloud_sdk.core.runtime_context.ContextProvider`
                   instances. Defaults to ``[IASContextProvider()]``.

    Raises:
        TypeError: If *app* is not a recognised framework application type.

    Example::

        from sap_cloud_sdk import bootstrap

        bootstrap(app)  # IASContextProvider by default

        # multiple providers:
        bootstrap(app, providers=[IASContextProvider(), MyCustomProvider()])
    """
    if not providers:
        from sap_cloud_sdk.core.runtime_context import IASContextProvider
        providers = [IASContextProvider()]
    _attach(app, providers)


def _attach(app: Any, providers: List[ContextProvider]) -> None:
    """Detect framework and register the appropriate context middleware."""
    try:
        from starlette.applications import Starlette
        from sap_cloud_sdk.core.runtime_context.starlette import StarletteContextMiddleware

        if isinstance(app, Starlette):
            app.add_middleware(StarletteContextMiddleware, providers=providers)
            return
    except ImportError:
        pass

    raise TypeError(
        f"bootstrap() does not recognise app type {type(app)!r}. "
        "Supported frameworks: Starlette/FastAPI. "
        "For other frameworks, register the middleware manually."
    )
