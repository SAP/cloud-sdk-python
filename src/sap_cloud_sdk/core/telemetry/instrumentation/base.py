import importlib.util
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class LibraryInstrumentor(ABC):
    """Base class for optional library instrumentors.

    Subclasses wrap a single opentelemetry-instrumentation-* package.
    The target library (e.g. httpx) is checked at runtime via find_spec so
    that missing optional dependencies are silently skipped rather than
    raising ImportError.

    kwargs passed to instrument() are forwarded to _instrument(), allowing
    subclasses to accept optional arguments (e.g. app= for framework instrumentors).
    """

    #: Import name of the library being instrumented (e.g. "httpx").
    library_name: str

    def instrument(self, **kwargs: Any) -> None:
        if not self._is_library_installed():
            logger.debug(
                "%s not installed, skipping instrumentation", self.library_name
            )
            return
        if self.is_instrumented():
            logger.debug("%s already instrumented", self.library_name)
            return
        self._instrument(**kwargs)
        logger.debug("Instrumented %s", self.library_name)

    def uninstrument(self) -> None:
        if not self.is_instrumented():
            return
        self._uninstrument()
        logger.debug("Uninstrumented %s", self.library_name)

    @abstractmethod
    def is_instrumented(self) -> bool: ...

    @abstractmethod
    def _instrument(self, **kwargs: Any) -> None: ...

    @abstractmethod
    def _uninstrument(self) -> None: ...

    def _is_library_installed(self) -> bool:
        return importlib.util.find_spec(self.library_name) is not None
