"""Internal base class for framework auto-instrumentation adapters."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from sap_cloud_sdk.core.telemetry.middleware.base import TelemetryMiddleware

logger = logging.getLogger(__name__)


class FrameworkInstrumentor(ABC):
    """Auto-instrumentation adapter for a specific web framework.

    Internal to the SDK — not part of the public API.

    Subclasses patch the framework at the class level so that any application
    created after ``instrument()`` is called automatically gets IAS telemetry
    middleware — no ``app=`` reference required.

    The idempotency guard lives here so subclasses never need to implement it.
    Subclasses implement ``_do_instrument`` / ``_do_uninstrument`` only.

    To add support for a new framework, create a new module under
    ``sap_cloud_sdk.core.telemetry.middleware`` (prefixed with ``_``) and
    decorate the class with ``@_register``::

        from sap_cloud_sdk.core.telemetry.middleware._registry import _register
        from sap_cloud_sdk.core.telemetry.middleware._framework_instrumentor import FrameworkInstrumentor

        @_register
        class _DjangoIASInstrumentor(FrameworkInstrumentor):
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
    supersedes: "type[TelemetryMiddleware] | None" = None

    def instrument(self) -> None:
        if self.__class__._instrumented:
            logger.debug("%s already instrumented, skipping", type(self).__name__)
            return
        self._do_instrument()
        self.__class__._instrumented = True
        logger.info("Instrumented %s", type(self).__name__)

    def uninstrument(self) -> None:
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
    def _do_instrument(self) -> None: ...

    @abstractmethod
    def _do_uninstrument(self) -> None: ...

    @abstractmethod
    def get_attributes(self) -> Dict[str, Any]: ...
