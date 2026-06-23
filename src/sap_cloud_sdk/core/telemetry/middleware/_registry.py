"""Internal registry for FrameworkInstrumentor subclasses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sap_cloud_sdk.core.telemetry.middleware._framework_instrumentor import FrameworkInstrumentor

logger = logging.getLogger(__name__)

_registry: list[type[FrameworkInstrumentor]] = []


def _register(cls: type[FrameworkInstrumentor]) -> type[FrameworkInstrumentor]:
    """Register a FrameworkInstrumentor subclass for auto-discovery.

    Internal decorator — not part of the public API::

        @_register
        class _StarletteIASInstrumentor(FrameworkInstrumentor):
            ...
    """
    _registry.append(cls)
    return cls


def _get_available() -> list[FrameworkInstrumentor]:
    """Return one instance of each registered instrumentor whose framework is installed."""
    available = []
    for cls in _registry:
        if cls.is_available():
            available.append(cls())
        else:
            logger.debug("%s skipped (framework not installed)", cls.__name__)
    return available
