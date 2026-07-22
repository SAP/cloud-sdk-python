"""ContextProvider protocol — the pluggable extraction interface."""

from typing import Protocol, runtime_checkable

from sap_cloud_sdk.core.runtime_context._context import RequestContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope


@runtime_checkable
class ContextProvider(Protocol):
    """Extracts a :class:`RequestContext` from a :class:`RequestEnvelope`.

    Implement this to add a new auth provider or header convention. The envelope
    is framework-agnostic — providers never touch Starlette, Flask, or gRPC types.

    Example::

        MY_KEY = ContextKey[str]("my_key")

        class MyProvider(ContextProvider):
            def extract(self, envelope: RequestEnvelope) -> RequestContext:
                value = envelope.headers.get("x-my-header", "")
                return RequestContext({MY_KEY: value} if value else {})
    """

    def extract(self, envelope: RequestEnvelope) -> RequestContext:  # pragma: no cover
        ...
