from opentelemetry.instrumentation.requests import RequestsInstrumentor

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = RequestsInstrumentor()


class RequestsInstrumentorWrapper(LibraryInstrumentor):
    """Instruments the requests library with OTel spans and W3C header propagation."""

    library_name = "requests"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self) -> None:
        _instrumentor.instrument()

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(RequestsInstrumentorWrapper())
