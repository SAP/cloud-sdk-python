from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = FastAPIInstrumentor()


class FastAPIInstrumentorWrapper(LibraryInstrumentor):
    """Instruments FastAPI with OTel spans for inbound HTTP requests and baggage extraction.

    Must be called before the FastAPI app instance is constructed, or pass the app
    instance via auto_instrument(app=app) from within a lifespan handler.
    """

    library_name = "fastapi"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self, **kwargs) -> None:
        from fastapi import FastAPI

        app = kwargs.get("app")
        if app is None or not isinstance(app, FastAPI):
            _instrumentor.instrument()
            return
        FastAPIInstrumentor.instrument_app(app)

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(FastAPIInstrumentorWrapper())
