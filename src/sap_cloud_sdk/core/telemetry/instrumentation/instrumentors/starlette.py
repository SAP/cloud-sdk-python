from opentelemetry.instrumentation.starlette import StarletteInstrumentor

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = StarletteInstrumentor()


class StarletteInstrumentorWrapper(LibraryInstrumentor):
    """Instruments Starlette with OTel spans for inbound HTTP requests and baggage extraction.

    Must be called before the Starlette app instance is constructed, or pass the app
    instance via auto_instrument(app=app) from within a lifespan handler.
    """

    library_name = "starlette"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self, **kwargs) -> None:
        from starlette.applications import Starlette
        app = kwargs.get("app")
        if app is None:
            _instrumentor.instrument()
            return
        if not isinstance(app, Starlette):
            raise TypeError(
                f"StarletteInstrumentorWrapper expects a Starlette instance, got {type(app).__name__}"
            )
        _instrumentor.instrument_app(app)

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(StarletteInstrumentorWrapper())
