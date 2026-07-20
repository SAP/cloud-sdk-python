from sap_cloud_sdk.core.telemetry.instrumentation.base import LibraryInstrumentor
from sap_cloud_sdk.core.telemetry.instrumentation._registry import register, get_registry

# Import concrete instrumentors to trigger their register() calls.
from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import (  # noqa: F401
    httpx,
    requests,
    grpc,
    logging,
)

# Optional — guarded so missing extras don't break the import.
try:
    from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import starlette  # noqa: F401
except ImportError:
    pass

try:
    from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import fastapi  # noqa: F401
except ImportError:
    pass

try:
    from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import aiohttp  # noqa: F401
except ImportError:
    pass

try:
    from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import sqlalchemy  # noqa: F401
except ImportError:
    pass

try:
    from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import redis  # noqa: F401
except ImportError:
    pass

try:
    from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import django  # noqa: F401
except ImportError:
    pass

try:
    from sap_cloud_sdk.core.telemetry.instrumentation.instrumentors import flask  # noqa: F401
except ImportError:
    pass

__all__ = [
    "LibraryInstrumentor",
    "register",
    "get_registry",
]
