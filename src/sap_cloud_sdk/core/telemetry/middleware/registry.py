"""Registry for FrameworkInstrumentor subclasses.

Instrumentors self-register via the ``@register`` decorator.  ``auto_instrument()``
calls ``get_available()`` to discover and activate all installed frameworks without
needing to know about any specific framework.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sap_cloud_sdk.core.telemetry.middleware.base import FrameworkInstrumentor

logger = logging.getLogger(__name__)

_registry: list[type[FrameworkInstrumentor]] = []


def register(cls: type[FrameworkInstrumentor]) -> type[FrameworkInstrumentor]:
    """Register a FrameworkInstrumentor subclass for auto-discovery.

    Use as a class decorator::

        @register
        class StarletteIASInstrumentor(FrameworkInstrumentor):
            ...
    """
    _registry.append(cls)
    return cls


def get_available() -> list[FrameworkInstrumentor]:
    """Return one instance of each registered instrumentor whose framework is installed."""
    available = []
    for cls in _registry:
        if cls.is_available():
            available.append(cls())
        else:
            logger.debug("%s skipped (framework not installed)", cls.__name__)
    return available
