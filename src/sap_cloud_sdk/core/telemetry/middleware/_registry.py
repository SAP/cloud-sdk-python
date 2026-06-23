"""Internal discovery for FrameworkInstrumentor subclasses.

Lists every known internal instrumentor in one place — adding a new framework
is a single try/except block in ``_discover_instrumentors``. No decorators,
no import-time side effects.

This is an internal SDK module — not part of the public API.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sap_cloud_sdk.core.telemetry.middleware._framework_instrumentor import (
        FrameworkInstrumentor,
    )

logger = logging.getLogger(__name__)


def _discover_instrumentors() -> list[type[FrameworkInstrumentor]]:
    """Return every internal instrumentor class whose module imports cleanly.

    Add a new framework by appending one try/except block here.
    """
    classes: list[type[FrameworkInstrumentor]] = []

    try:
        from sap_cloud_sdk.core.telemetry.middleware._starlette_instrumentor import (
            _StarletteIASInstrumentor,
        )
        classes.append(_StarletteIASInstrumentor)
    except ImportError:
        logger.debug("_StarletteIASInstrumentor unavailable (starlette not installed)")

    return classes


def _get_available() -> list[FrameworkInstrumentor]:
    """Return one instance of each discovered instrumentor whose framework is installed."""
    return [cls() for cls in _discover_instrumentors() if cls.is_available()]
