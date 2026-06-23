"""HTTP framework middleware integration for Cloud SDK telemetry.

Provides middleware adapters that extract request-scoped attributes
(e.g. A2A session/task headers) and surface them as OpenTelemetry span
attributes via auto_instrument().
"""

from sap_cloud_sdk.core.telemetry.middleware.base import (
    FrameworkInstrumentor,
    TelemetryMiddleware,
)
from sap_cloud_sdk.core.telemetry.middleware.registry import register

__all__ = [
    "FrameworkInstrumentor",
    "TelemetryMiddleware",
    "register",
]

try:
    from sap_cloud_sdk.core.telemetry.middleware.starlette_a2a import (
        StarletteIASTelemetryMiddleware,
    )

    __all__ += ["StarletteIASTelemetryMiddleware"]
except ImportError:
    pass

try:
    import sap_cloud_sdk.core.telemetry.middleware.starlette_instrumentor  # noqa: F401 — triggers @register
except ImportError:
    pass
