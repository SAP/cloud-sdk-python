"""Top-level bootstrap() entry point for the SAP Cloud SDK."""

from dataclasses import dataclass
from typing import Any, List, Optional

from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._registry import get_registry, record_attached
from sap_cloud_sdk.core.runtime_context import (
    DWCContextProvider,
    IASContextProvider,
    SAPTriggerContextProvider,
)
from sap_cloud_sdk.core.telemetry import Module, Operation
from sap_cloud_sdk.core.telemetry.auto_instrument import auto_instrument
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics


@dataclass
class TelemetryConfig:
    """Telemetry options for :func:`bootstrap`.

    Attributes:
        disable_traces: Skip OpenTelemetry trace initialisation entirely.
        disable_batch:  Use :class:`~opentelemetry.sdk.trace.export.SimpleSpanProcessor`
                        (synchronous) instead of
                        :class:`~opentelemetry.sdk.trace.export.BatchSpanProcessor`
                        (asynchronous, recommended for production).
    """

    disable_traces: bool = False
    disable_batch: bool = False


@record_metrics(Module.BOOTSTRAP, Operation.BOOTSTRAP)
def bootstrap(
    app: Any,
    providers: Optional[List[ContextProvider]] = None,
    telemetry: Optional[TelemetryConfig] = None,
) -> None:
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
        telemetry: Optional :class:`TelemetryConfig` to tune or disable individual
                   telemetry signals.

    Raises:
        TypeError: If no registered adapter recognises *app*.

    Example::

        from sap_cloud_sdk import bootstrap, TelemetryConfig

        bootstrap(app)  # IAS + SAP trigger + DWC, telemetry auto-configured from env

        # disable traces:
        bootstrap(app, telemetry=TelemetryConfig(disable_traces=True))

        # custom providers:
        bootstrap(app, providers=[IASContextProvider(), MyProvider()])
    """
    cfg = telemetry or TelemetryConfig()

    if not cfg.disable_traces:
        auto_instrument(app=app, disable_batch=cfg.disable_batch)

    if not providers:
        providers = [
            IASContextProvider(),
            SAPTriggerContextProvider(),
            DWCContextProvider(),
        ]

    for adapter in get_registry():
        if adapter.matches(app):
            adapter.attach(app, providers)
            record_attached(adapter.name)
            return

    raise TypeError(
        f"bootstrap() does not recognise app type {type(app)!r}. "
        "Supported frameworks are determined by registered FrameworkAdapters. "
        "For other frameworks, register a FrameworkAdapter or attach the middleware manually."
    )
