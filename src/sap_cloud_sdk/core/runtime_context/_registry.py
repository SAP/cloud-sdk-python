"""Framework adapter base class and registry for bootstrap()."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List

from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider

logger = logging.getLogger(__name__)

_registry: List[FrameworkAdapter] = []
_attached: List[str] = []


def register(adapter: FrameworkAdapter) -> None:
    """Register a framework adapter with the bootstrap registry."""
    _registry.append(adapter)


def get_registry() -> List[FrameworkAdapter]:
    return list(_registry)


def record_attached(name: str) -> None:
    """Record a framework adapter as attached. Called by bootstrap()."""
    _attached.append(name)


def get_framework_adapters() -> List[str]:
    """Return the names of framework adapters attached via bootstrap().

    Each entry corresponds to one :func:`~sap_cloud_sdk.bootstrap` call that
    successfully matched and attached an adapter (e.g. ``"starlette"``).
    Returns an empty list if bootstrap() has not been called yet.
    """
    return list(_attached)


class FrameworkAdapter(ABC):
    """Connects a framework or invocation source to the SDK runtime context.

    Subclasses know how to detect a specific app type and attach the SDK's
    context pipeline to it. Register at module level so that
    :func:`~sap_cloud_sdk.core.bootstrap.bootstrap` can discover them without
    importing framework-specific code directly.

    Example::

        class FlaskContextAdapter(FrameworkAdapter):
            name = "flask"

            def _matches(self, app) -> bool:
                from flask import Flask
                return isinstance(app, Flask)

            def attach(self, app, providers) -> None:
                app.before_request(lambda: ...)

        register(FlaskContextAdapter())
    """

    #: Human-readable identifier for this adapter (e.g. ``"starlette"``).
    name: str

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
