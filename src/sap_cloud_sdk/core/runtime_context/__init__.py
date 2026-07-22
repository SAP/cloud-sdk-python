"""SDK-wide runtime context for the current execution.

Lets SDK modules read caller-identity information (tenant, user, trigger type)
without knowing about the invocation source — HTTP, gRPC, message queue, etc.

Wire once at startup::

    from sap_cloud_sdk import bootstrap

    bootstrap(app)  # defaults to IASContextProvider + HeaderContextProvider

Then read anywhere::

    from sap_cloud_sdk.core.runtime_context import get_context, TENANT_ID, USER_ID

    ctx = get_context()
    ctx.get(TENANT_ID)   # -> "abc-123" or None
    ctx.get(USER_ID)     # -> "user-uuid" or None
"""

from sap_cloud_sdk.core.runtime_context._context import (
    RuntimeContext,
    get_context,
)
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import ContextKey, TRIGGER_TYPE
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._registry import FrameworkAdapter, register
from sap_cloud_sdk.core.runtime_context.providers import (
    HeaderContextProvider,
    IASContextProvider,
    GLOBAL_TENANT_ID,
    TENANT_ID,
    USER_ID,
)

# Register built-in framework adapters (guarded so missing extras don't break the import).
import sap_cloud_sdk.core.runtime_context.adapters  # noqa: F401

__all__ = [
    "ContextKey",
    "ContextProvider",
    "FrameworkAdapter",
    "GLOBAL_TENANT_ID",
    "HeaderContextProvider",
    "IASContextProvider",
    "RuntimeContext",
    "RequestEnvelope",
    "TENANT_ID",
    "TRIGGER_TYPE",
    "USER_ID",
    "get_context",
    "register",
]
