from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = HTTPXClientInstrumentor()


class HttpxInstrumentor(LibraryInstrumentor):
    """Instruments httpx sync and async clients with OTel spans and W3C header propagation."""

    library_name = "httpx"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self) -> None:
        _instrumentor.instrument()

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(HttpxInstrumentor())
