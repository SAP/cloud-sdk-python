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
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry._instrument import _instrument


@record_metrics(Module.BOOTSTRAP, Operation.BOOTSTRAP)
def bootstrap(
    app: Any = None,
    providers: Optional[List[ContextProvider]] = None,
    disable_batch: bool = False,
) -> None:
    """Wire the SDK into your application framework and initialize telemetry.

    Call once at startup. Performs two things:

    1. **Telemetry** — initialises OpenTelemetry tracing (exporting to the
       endpoint in ``OTEL_EXPORTER_OTLP_ENDPOINT``, or console when
       ``OTEL_TRACES_EXPORTER=console``).

    2. **Runtime context** — attaches middleware to *app* so that on every
       inbound request the SDK runs all *providers*, merges the results, and
       makes them available via
       :func:`~sap_cloud_sdk.core.runtime_context.get_context`.
       Skipped when *app* is ``None`` (e.g. background workers, scripts).

    The framework is detected automatically from the *app* type via the
    registered :class:`~sap_cloud_sdk.core.runtime_context.FrameworkAdapter`
    instances.

    Args:
        app:           Application instance to attach the middleware to.
                       Pass ``None`` to skip framework wiring (telemetry still
                       initializes).
        providers:     Context providers to run on each request. Defaults to
                       ``[IASContextProvider(), SAPTriggerContextProvider(),
                       DWCContextProvider()]``.
        disable_batch: Pass ``True`` to use ``SimpleSpanProcessor`` instead of
                       ``BatchSpanProcessor``. Useful in tests or scripts.

    Raises:
        TypeError: If *app* is not ``None`` and no registered adapter
                   recognises it.

    Example::

        from sap_cloud_sdk import bootstrap

        bootstrap(app)                     # IAS + SAP trigger + DWC by default
        bootstrap(app, disable_batch=True) # synchronous span export
        bootstrap()                        # telemetry only, no framework wiring
    """
    _instrument(disable_batch=disable_batch, app=app)

    if app is None:
        return

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
