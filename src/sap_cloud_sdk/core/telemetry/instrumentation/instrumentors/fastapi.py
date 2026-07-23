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
        if app is not None:
            if not isinstance(app, FastAPI):
                raise TypeError(
                    f"FastAPIInstrumentorWrapper expects a FastAPI instance, got {type(app).__name__}"
                )
            FastAPIInstrumentor.instrument_app(app)
        else:
            _instrumentor.instrument()

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(FastAPIInstrumentorWrapper())
