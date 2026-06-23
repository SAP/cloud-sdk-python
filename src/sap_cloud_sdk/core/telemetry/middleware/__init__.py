"""HTTP framework middleware integration for Cloud SDK telemetry.

The explicit middleware path (``TelemetryMiddleware``, ``StarletteIASTelemetryMiddleware``,
and the ``middlewares=`` parameter of ``auto_instrument()``) is deprecated and will be
removed in the next major version. Call ``auto_instrument()`` before creating your app
instead — IAS middleware is registered automatically.
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

# Trigger @_register side-effect for the internal Starlette instrumentor.
try:
    import sap_cloud_sdk.core.telemetry.middleware._starlette_instrumentor  # noqa: F401
except ImportError:
    pass
