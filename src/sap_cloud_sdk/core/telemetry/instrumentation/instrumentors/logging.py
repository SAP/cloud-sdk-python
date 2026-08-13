import logging as stdlib_logging

from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.logging.handler import (
    LoggingHandler as _InstrumentationHandler,
)

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = LoggingInstrumentor()


def _has_otel_handler_on_root() -> bool:
    """Return True if any OTel log bridge handler is already on the root logger."""
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
        if _has_otel_handler_on_root():
            # An OTel log bridge handler is already on root (from platform
            # auto-instrumentation or setup_log_provider). Pass
            # enable_log_auto_instrumentation=False so LoggingInstrumentor
            # only injects trace context into stdlib log records — it must
            # not add a second handler that would duplicate every log record.
            kwargs = {**kwargs, "enable_log_auto_instrumentation": False}
        _instrumentor.instrument(**kwargs)

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(LoggingInstrumentorWrapper())
