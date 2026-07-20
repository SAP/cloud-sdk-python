from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_instrumentor = SQLAlchemyInstrumentor()


class SQLAlchemyInstrumentorWrapper(LibraryInstrumentor):
    library_name = "sqlalchemy"

    def is_instrumented(self) -> bool:
        return _instrumentor.is_instrumented_by_opentelemetry

    def _instrument(self) -> None:
        _instrumentor.instrument()

    def _uninstrument(self) -> None:
        _instrumentor.uninstrument()


register(SQLAlchemyInstrumentorWrapper())
