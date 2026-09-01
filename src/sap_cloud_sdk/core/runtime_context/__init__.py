"""SDK-wide runtime context for the current execution.

Lets SDK modules read caller-identity information (tenant, user, trigger type)
without knowing about the invocation source — HTTP, gRPC, message queue, etc.

Wire once at startup::

    from sap_cloud_sdk import bootstrap

    bootstrap(app)  # defaults to IASContextProvider + SAPTriggerContextProvider + DWCContextProvider

Then read anywhere::

    from sap_cloud_sdk.core.runtime_context import get_context, APP_TENANT_ID, USER_ID

    ctx = get_context()
    ctx.get(APP_TENANT_ID)   # -> "abc-123" or None
    ctx.get(USER_ID)     # -> "user-uuid" or None
"""

from sap_cloud_sdk.core.runtime_context._context import (
    RuntimeContext,
    get_context,
    is_feature_enabled,
)
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import (
    ContextKey,
    DWC_SUBDOMAIN,
    DWC_TENANT,
    FEATURE_TOGGLES,
    TRIGGER_TYPE,
)
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._registry import (
    Adapter,
    FrameworkAdapter,
    get_attached_adapters,
    register,
)
from sap_cloud_sdk.core.runtime_context.providers import (
    DWCContextProvider,
    IASContextProvider,
    SAPTriggerContextProvider,
    APP_TENANT_ID,
    GLOBAL_TENANT_ID,
    USER_ID,
)

# Register built-in framework adapters (guarded so missing extras don't break the import).
import sap_cloud_sdk.core.runtime_context.adapters  # noqa: F401

__all__ = [
    "Adapter",
    "APP_TENANT_ID",
    "ContextKey",
    "ContextProvider",
    "DWC_SUBDOMAIN",
    "DWC_TENANT",
    "DWCContextProvider",
    "FEATURE_TOGGLES",
    "FrameworkAdapter",
    "get_attached_adapters",
    "GLOBAL_TENANT_ID",
    "IASContextProvider",
    "RuntimeContext",
    "RequestEnvelope",
    "SAPTriggerContextProvider",
    "TRIGGER_TYPE",
    "USER_ID",
    "get_context",
    "is_feature_enabled",
    "register",
]
