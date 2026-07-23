from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = AioHttpClientInstrumentor()


class AiohttpInstrumentor(LibraryInstrumentor):
    """Instruments aiohttp client sessions with OTel spans and W3C header propagation."""

    library_name = "aiohttp"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self) -> None:
        _instrumentor.instrument()

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(AiohttpInstrumentor())
