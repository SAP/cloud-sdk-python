"""Abstract base classes for telemetry middleware adapters."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TelemetryMiddleware(ABC):
    """Abstract base for HTTP framework middleware that extracts telemetry attributes.

    Implementations register with their application via ``register()``, extract
    per-request attributes into a ContextVar during each request, and expose them
    via ``get_attributes()``. The SDK calls ``register()`` and wires a
    ``MiddlewareSpanProcessor`` that stamps those attributes onto every span.
    """

    framework_key: str = ""  # override to match the FrameworkInstrumentor.framework_key for the same framework

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


class FrameworkInstrumentor(ABC):
    """Auto-instrumentation adapter for a specific web framework.

    Subclasses patch the framework at the class level so that any application
    created after ``instrument()`` is called automatically.

    The idempotency guard lives here so subclasses never need to implement it.
    Subclasses implement ``_do_instrument`` / ``_do_uninstrument`` only.

    Usage (adding a new framework):

        from sap_cloud_sdk.core.telemetry.middleware import register
        from sap_cloud_sdk.core.telemetry.middleware.base import FrameworkInstrumentor

        @register
        class DjangoIASInstrumentor(FrameworkInstrumentor):
            @classmethod
            def is_available(cls) -> bool:
                try:
                    import django  # noqa: F401
                    return True
                except ImportError:
                    return False

            def _do_instrument(self) -> None: ...
            def _do_uninstrument(self) -> None: ...
            def get_attributes(self) -> Dict[str, Any]: ...
    """

    _instrumented: bool = False
    _processor_registered: bool = False
    framework_key: str = ""  # override in subclasses to enable overlap detection with TelemetryMiddleware

    def instrument(self) -> None:
        """Patch the framework. Idempotent — safe to call multiple times."""
        if self.__class__._instrumented:
            logger.debug("%s already instrumented, skipping", type(self).__name__)
            return
        self._do_instrument()
        self.__class__._instrumented = True
        logger.info("Instrumented %s", type(self).__name__)

    def uninstrument(self) -> None:
        """Restore the framework to its original state. Idempotent."""
        if not self.__class__._instrumented:
            return
        self._do_uninstrument()
        self.__class__._instrumented = False
        self.__class__._processor_registered = False
        logger.debug("Uninstrumented %s", type(self).__name__)

    @classmethod
    def is_available(cls) -> bool:
        """Return True when the target framework is importable.

        Override in each subclass with a try/except import check.
        """
        return False

    @abstractmethod
    def _do_instrument(self) -> None:
        """Perform the actual framework patch. Called once by ``instrument()``."""

    @abstractmethod
    def _do_uninstrument(self) -> None:
        """Restore the framework. Called once by ``uninstrument()``."""

    @abstractmethod
    def get_attributes(self) -> Dict[str, Any]:
        """Return IAS attributes extracted from the current request context."""
