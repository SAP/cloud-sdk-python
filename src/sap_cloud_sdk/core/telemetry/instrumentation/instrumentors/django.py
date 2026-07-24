from opentelemetry.instrumentation.django import DjangoInstrumentor

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = DjangoInstrumentor()


class DjangoInstrumentorWrapper(LibraryInstrumentor):
    """Instruments Django with OTel spans for inbound HTTP requests and baggage extraction."""

    library_name = "django"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self, **kwargs) -> None:
        _instrumentor.instrument()

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(DjangoInstrumentorWrapper())
