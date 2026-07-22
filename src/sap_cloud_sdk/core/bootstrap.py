"""Top-level bootstrap() entry point for the SAP Cloud SDK."""

from typing import Any, List, Optional

from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._registry import get_registry
from sap_cloud_sdk.core.runtime_context import HeaderContextProvider, IASContextProvider


def bootstrap(app: Any, providers: Optional[List[ContextProvider]] = None) -> None:
    """Wire the SDK runtime context into your application framework.

    Call once at startup. On every inbound request the SDK will run all
    *providers* against the request, merge the results, and make them
    available via :func:`~sap_cloud_sdk.core.runtime_context.get_context`.

    The framework is detected automatically from the *app* type via the
    registered :class:`~sap_cloud_sdk.core.runtime_context.FrameworkAdapter`
    instances — adding support for a new framework never requires editing
    this function.

    Args:
        app:       The application instance to attach the middleware to.
        providers: Context providers to run on each request. Defaults to
                   ``[IASContextProvider(), HeaderContextProvider()]``.

    Raises:
        TypeError: If no registered adapter recognises *app*.

    Example::

        from sap_cloud_sdk import bootstrap

        bootstrap(app)  # IAS + SAP headers by default

        # custom providers:
        bootstrap(app, providers=[IASContextProvider(), MyProvider()])
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
