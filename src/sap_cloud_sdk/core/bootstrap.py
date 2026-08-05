"""Top-level bootstrap() entry point for the SAP Cloud SDK."""

from typing import Any, List, Optional

from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._registry import get_registry
from sap_cloud_sdk.core.runtime_context import (
    DWCContextProvider,
    IASContextProvider,
    SAPTriggerContextProvider,
)
from sap_cloud_sdk.core.telemetry import Module, Operation
from sap_cloud_sdk.core.telemetry.auto_instrument import auto_instrument
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics


@record_metrics(Module.BOOTSTRAP, Operation.BOOTSTRAP)
def bootstrap(app: Any, providers: Optional[List[ContextProvider]] = None) -> None:
    """Wire the SDK runtime context into your application framework.

    Call once at startup. On every inbound request the SDK will run all
    *providers* against the request, merge the results, and make them
    available via :func:`~sap_cloud_sdk.core.runtime_context.get_context`.

    The framework is detected automatically from the *app* type via the
    registered :class:`~sap_cloud_sdk.core.runtime_context.FrameworkAdapter`
    instances — adding support for a new framework never requires editing
    this function.

    Also calls :func:`~sap_cloud_sdk.core.telemetry.auto_instrument` automatically.
    Telemetry is a no-op unless ``OTEL_EXPORTER_OTLP_ENDPOINT`` or
    ``OTEL_TRACES_EXPORTER=console`` is set in the environment.

    Args:
        app:       The application instance to attach the middleware to.
        providers: Context providers to run on each request. Defaults to
                   ``[IASContextProvider(), SAPTriggerContextProvider(), DWCContextProvider()]``.

    Raises:
        TypeError: If no registered adapter recognises *app*.

    Example::

        from sap_cloud_sdk import bootstrap

        bootstrap(app)  # IAS + SAP trigger + DWC by default

        # custom providers:
        bootstrap(app, providers=[IASContextProvider(), MyProvider()])
    """
    auto_instrument(app=app)

    if not providers:
        providers = [
            IASContextProvider(),
            SAPTriggerContextProvider(),
            DWCContextProvider(),
        ]

    for adapter in get_registry():
        if adapter.matches(app):
            adapter.attach(app, providers)
            return

    raise TypeError(
        f"bootstrap() does not recognise app type {type(app)!r}. "
        "Supported frameworks are determined by registered FrameworkAdapters. "
        "For other frameworks, register a FrameworkAdapter or attach the middleware manually."
    )
