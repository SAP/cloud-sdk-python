"""Framework adapter base class and registry for bootstrap()."""

import logging
from abc import ABC, abstractmethod
from typing import List

from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider

logger = logging.getLogger(__name__)

_registry: List["FrameworkAdapter"] = []


def register(adapter: "FrameworkAdapter") -> None:
    """Register a framework adapter with the bootstrap registry."""
    _registry.append(adapter)


def get_registry() -> List["FrameworkAdapter"]:
    return list(_registry)


class FrameworkAdapter(ABC):
    """Base class for framework-specific context middleware adapters.

    Subclasses know how to detect a framework's app object and attach the
    appropriate context middleware to it. Register at module level so that
    :func:`~sap_cloud_sdk.core.bootstrap.bootstrap` can discover them without
    importing framework-specific code directly.

    Example::

        class FlaskContextAdapter(FrameworkAdapter):
            def _matches(self, app) -> bool:
                from flask import Flask
                return isinstance(app, Flask)

            def attach(self, app, providers) -> None:
                app.before_request(lambda: ...)

        register(FlaskContextAdapter())
    """

    def matches(self, app) -> bool:
        """Return True if this adapter handles *app*'s framework type."""
        try:
            return self._matches(app)
        except ImportError:
            return False

    @abstractmethod
    def _matches(self, app) -> bool: ...

    @abstractmethod
    def attach(self, app, providers: List[ContextProvider]) -> None: ...
