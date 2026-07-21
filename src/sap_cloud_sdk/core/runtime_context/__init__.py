"""SDK-wide per-request runtime context.

Provides a provider-agnostic way for SDK modules to access caller-identity
fields (tenant, user, trigger type) without coupling to a specific auth
provider or HTTP framework.

Typical usage — wire once at app startup::

    from sap_cloud_sdk import bootstrap
    from sap_cloud_sdk.core.runtime_context import IASContextProvider

    bootstrap(app, provider=IASContextProvider())

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
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.core.runtime_context._providers import IASContextProvider

__all__ = [
    "ContextProvider",
    "IASContextProvider",
    "RequestContext",
    "async_sdk_context",
    "get_context",
    "sdk_context",
    "set_context",
]
