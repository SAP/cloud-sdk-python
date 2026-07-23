from opentelemetry.instrumentation.logging import LoggingInstrumentor

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = LoggingInstrumentor()


class LoggingInstrumentorWrapper(LibraryInstrumentor):
    """Injects trace_id and span_id into every stdlib log record for log-trace correlation."""

    library_name = "logging"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self) -> None:
        _instrumentor.instrument(set_logging_format=True)

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(LoggingInstrumentorWrapper())
