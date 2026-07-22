"""Top-level bootstrap() entry point for the SAP Cloud SDK."""

from typing import Any, List, Optional

from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._registry import get_registry
from sap_cloud_sdk.core.runtime_context import HeaderContextProvider, IASContextProvider

def bootstrap(app: Any, providers: Optional[List[ContextProvider]] = None) -> None:
    """Wire the SDK runtime context into your application framework.

    Call this once at application startup. The SDK will attach a middleware
    to *app* that populates :class:`~sap_cloud_sdk.core.runtime_context.RequestContext`
    on every inbound request by running all *providers* against it and merging
    the results.

    After bootstrapping, any SDK module (auditlog, telemetry, etc.) can call
    :func:`~sap_cloud_sdk.core.runtime_context.get_context` to read
    tenant/user information without knowing about headers or auth providers.

    The framework is detected automatically from the *app* type. Supported
    frameworks are determined by registered
    :class:`~sap_cloud_sdk.core.runtime_context.FrameworkAdapter` instances —
    new frameworks are added by registering an adapter, not by editing this file.

    Args:
        app:       The application instance to attach the middleware to.
        providers: One or more :class:`~sap_cloud_sdk.core.runtime_context.ContextProvider`
                   instances. Defaults to ``[IASContextProvider()]``.

    Raises:
        TypeError: If no registered adapter recognises *app*.

    Example::

        from sap_cloud_sdk import bootstrap

        bootstrap(app)  # IASContextProvider by default

        # multiple providers:
        bootstrap(app, providers=[IASContextProvider(), MyCustomProvider()])
    """
    if not providers:
        providers = [IASContextProvider(), HeaderContextProvider()]

    for adapter in get_registry():
        if adapter.matches(app):
            adapter.attach(app, providers)
            return

    raise TypeError(
        f"bootstrap() does not recognise app type {type(app)!r}. "
        "Supported frameworks are determined by registered FrameworkAdapters. "
        "For other frameworks, register a FrameworkAdapter or attach the middleware manually."
    )
