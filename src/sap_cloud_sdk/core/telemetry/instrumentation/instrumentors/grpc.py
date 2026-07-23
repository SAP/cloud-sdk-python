from opentelemetry.instrumentation.grpc import (
    GrpcInstrumentorClient,
    GrpcInstrumentorServer,
)

from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register

_client_instrumentor = GrpcInstrumentorClient()
_server_instrumentor = GrpcInstrumentorServer()


class GrpcInstrumentorWrapper(LibraryInstrumentor):
    """Instruments gRPC client and server interceptors with OTel spans."""

    library_name = "grpc"

    def is_instrumented(self) -> bool:
        return (
            _client_instrumentor.is_instrumented_by_opentelemetry
            or _server_instrumentor.is_instrumented_by_opentelemetry
        )

    def _instrument(self) -> None:
        _client_instrumentor.instrument()
        _server_instrumentor.instrument()

    def _uninstrument(self) -> None:
        _client_instrumentor.uninstrument()
        _server_instrumentor.uninstrument()


register(GrpcInstrumentorWrapper())
