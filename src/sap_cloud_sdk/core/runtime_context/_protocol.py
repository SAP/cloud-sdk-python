"""ContextProvider protocol — the pluggable extraction interface."""

from typing import Protocol, runtime_checkable

from sap_cloud_sdk.core.runtime_context._context import RequestContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope


@runtime_checkable
class ContextProvider(Protocol):
    """Extract a :class:`RequestContext` from a :class:`RequestEnvelope`.

    Implement this protocol to teach the SDK how to read caller-identity
    information from a specific auth provider (IAS, XSUAA, etc.).

    The envelope is framework-agnostic — providers never touch Starlette,
    Flask, or gRPC types directly. The framework middleware is responsible
    for building the envelope.

    Example::

        class MyProvider(ContextProvider):
            def extract(self, envelope: RequestEnvelope) -> RequestContext:
                token = envelope.headers.get("x-my-token", "")
                return RequestContext(tenant_id=decode(token).tenant)
    """

    def extract(self, envelope: RequestEnvelope) -> RequestContext:  # pragma: no cover
        ...
