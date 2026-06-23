"""Internal: auto-instrumentation adapter base class.

This is an internal SDK module — not part of the public API.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FrameworkInstrumentor(ABC):
    """Internal auto-instrumentation adapter for a specific web framework.

    Subclasses patch the framework at the class level so that any application
    created after ``instrument()`` is called automatically gets the IAS
    telemetry middleware.

    The idempotency guard lives in the base class. Subclasses implement
    ``_do_instrument`` and ``_do_uninstrument`` only.
    """

    _instrumented: bool = False
    _processor_registered: bool = False

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
        """Return True when the target framework is importable."""
        return False

    @abstractmethod
    def _do_instrument(self) -> None:
        """Perform the actual framework patch."""

    @abstractmethod
    def _do_uninstrument(self) -> None:
        """Restore the framework to its pre-patch state."""

    @abstractmethod
    def get_attributes(self) -> Dict[str, Any]:
        """Return IAS attributes extracted from the current request context."""
