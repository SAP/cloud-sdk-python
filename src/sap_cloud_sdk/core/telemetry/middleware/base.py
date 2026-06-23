"""Public base class for explicit middleware adapters (deprecated path)."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from typing_extensions import deprecated


@deprecated(
    "TelemetryMiddleware is deprecated and will be removed in the next major version. "
    "Call auto_instrument() without middlewares= instead."
)
class TelemetryMiddleware(ABC):
    """Abstract base for explicit HTTP framework middleware.

    .. deprecated::
        Use ``auto_instrument()`` without ``middlewares=`` instead.
        ``TelemetryMiddleware`` and the explicit ``middlewares=`` parameter will
        be removed in the next major version.

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
        """Return middleware-extracted attributes for the current request context."""
