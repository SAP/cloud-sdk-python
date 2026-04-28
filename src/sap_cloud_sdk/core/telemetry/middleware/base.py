"""Abstract base class for telemetry middleware adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class TelemetryMiddleware(ABC):
    """Abstract base for HTTP framework middleware that extracts telemetry attributes.

    Concrete implementations wrap a framework-native middleware class and are
    responsible for:
      1. Registering themselves with the application via ``register(app)``.
      2. Extracting per-request attributes (headers, etc.) into a ContextVar.
      3. Returning the current context attributes via ``get_attributes()``.

    Users pass instances to ``auto_instrument(middlewares=[...])``. The SDK
    calls ``register(app)`` and wires a ``MiddlewareSpanProcessor`` that reads
    ``get_attributes()`` on every span start.
    """

    @abstractmethod
    def register(self, app: Any) -> None:
        """Register this middleware with the given framework application.

        Concrete implementations typically store ``app`` at construction time
        and may ignore this argument, using ``self.app`` instead.

        Args:
            app: The ASGI/WSGI application or framework app object.
        """

    @abstractmethod
    def get_attributes(self) -> Dict[str, Any]:
        """Return middleware-extracted attributes for the current request context.

        Returns:
            Dict of attribute key-value pairs set during the current request,
            or an empty dict when called outside a request context.
        """
