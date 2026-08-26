import logging as stdlib_logging

from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.logging.handler import (
    LoggingHandler as _InstrumentationHandler,
)

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = LoggingInstrumentor()


def _has_otel_handler_on_root() -> bool:
    # sitecustomize.py installs sdk._logs.LoggingHandler, not the instrumentation-layer one — check both.
    try:
        from opentelemetry.sdk._logs import LoggingHandler as _SDKHandler

        handler_types: tuple[type, ...] = (_InstrumentationHandler, _SDKHandler)
    except ImportError:
        handler_types = (_InstrumentationHandler,)
    return any(
        isinstance(h, handler_types) for h in stdlib_logging.getLogger().handlers
    )


class LoggingInstrumentorWrapper(LibraryInstrumentor):
    """Injects trace_id and span_id into every stdlib log record for log-trace correlation."""

    library_name = "logging"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self, **kwargs) -> None:
        kwargs.setdefault("set_logging_format", True)
        if _has_otel_handler_on_root():
            # Already have a handler — adding another duplicates every log record.
            kwargs = {**kwargs, "enable_log_auto_instrumentation": False}
        _instrumentor.instrument(**kwargs)

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(LoggingInstrumentorWrapper())
