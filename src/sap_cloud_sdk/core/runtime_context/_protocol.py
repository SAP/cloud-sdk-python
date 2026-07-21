"""ContextProvider protocol — the pluggable extraction interface."""

from typing import Any, Protocol, runtime_checkable

from sap_cloud_sdk.core.runtime_context._context import RequestContext


@runtime_checkable
class ContextProvider(Protocol):
    """Extract a :class:`RequestContext` from a framework-specific request object.

    Implement this protocol to teach the SDK how to read caller-identity
    information from a new framework (Flask, gRPC, raw WSGI, etc.).

    Example::

        class MyProvider(ContextProvider):
            def extract(self, request: MyRequest) -> RequestContext:
                return RequestContext(tenant_id=request.tenant, user_id=request.user)
    """

    def extract(self, request: Any) -> RequestContext:  # pragma: no cover
        ...
