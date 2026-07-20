from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = FastAPIInstrumentor()


class FastAPIInstrumentorWrapper(LibraryInstrumentor):
    library_name = "fastapi"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self) -> None:
        _instrumentor.instrument()

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(FastAPIInstrumentorWrapper())
