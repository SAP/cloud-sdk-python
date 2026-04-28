"""Abstract base class for telemetry middleware adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class TelemetryMiddleware(ABC):
    """Abstract base for HTTP framework middleware that extracts telemetry attributes.

    Implementations register with their application via ``register()``, extract
    per-request attributes into a ContextVar during each request, and expose them
    via ``get_attributes()``. The SDK calls ``register()`` and wires a
    ``MiddlewareSpanProcessor`` that stamps those attributes onto every span.
    """

    @abstractmethod
    def register(self) -> None:
        """Register this middleware with the framework application."""

    @abstractmethod
    def get_attributes(self) -> Dict[str, Any]:
        """Return middleware-extracted attributes for the current request context.

        Returns:
            Dict of attribute key-value pairs set during the current request,
            or an empty dict when called outside a request context.
        """
