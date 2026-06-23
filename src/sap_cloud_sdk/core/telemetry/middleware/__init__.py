"""HTTP framework middleware integration for Cloud SDK telemetry.

Provides middleware adapters that extract request-scoped attributes
(e.g. A2A session/task headers) and surface them as OpenTelemetry span
attributes via auto_instrument().
"""

from sap_cloud_sdk.core.telemetry.middleware.base import TelemetryMiddleware

__all__ = [
    "TelemetryMiddleware",
]

try:
    from sap_cloud_sdk.core.telemetry.middleware.starlette_a2a import (
        StarletteIASTelemetryMiddleware,
    )

    __all__ += ["StarletteIASTelemetryMiddleware"]
except ImportError:
    pass

try:
    # Side-effect import: triggers @_register so the instrumentor is discoverable.
    import sap_cloud_sdk.core.telemetry.middleware._starlette_instrumentor  # noqa: F401
except ImportError:
    pass
