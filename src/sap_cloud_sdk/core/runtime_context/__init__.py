"""SDK-wide per-request runtime context.

Provides a provider-agnostic way for SDK modules to access caller-identity
fields (tenant, user, trigger type) without coupling to a specific auth
provider or HTTP framework.

Typical usage — wire once at app startup::

    from sap_cloud_sdk import bootstrap
    from sap_cloud_sdk.core.runtime_context import IASContextProvider

    bootstrap(app, providers=[IASContextProvider()])

Then read anywhere in the SDK or application code::

    from sap_cloud_sdk.core.runtime_context import get_context

    ctx = get_context()
    print(ctx.tenant_id)    # e.g. "abc-123"
    print(ctx.user_id)      # e.g. "user-uuid"

For tests or CLI usage without HTTP::

    from sap_cloud_sdk.core.runtime_context import sdk_context, RequestContext

    with sdk_context(RequestContext(tenant_id="test-tenant")):
        ...  # get_context() returns that context here
"""

from sap_cloud_sdk.core.runtime_context._context import (
    RequestContext,
    async_sdk_context,
    get_context,
    sdk_context,
    set_context,
)
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import ContextKey, TRIGGER_TYPE
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._registry import FrameworkAdapter, register
from sap_cloud_sdk.core.runtime_context.providers import (
    HeaderContextProvider,
    IASContextProvider,
    IAS_CLAIMS,
    TENANT_ID,
    USER_ID,
)

# Register built-in framework adapters (guarded so missing extras don't break the import).
import sap_cloud_sdk.core.runtime_context.adapters  # noqa: F401

__all__ = [
    "ContextKey",
    "ContextProvider",
    "FrameworkAdapter",
    "HeaderContextProvider",
    "IAS_CLAIMS",
    "IASContextProvider",
    "RequestContext",
    "RequestEnvelope",
    "TENANT_ID",
    "TRIGGER_TYPE",
    "USER_ID",
    "async_sdk_context",
    "get_context",
    "register",
    "sdk_context",
    "set_context",
]
