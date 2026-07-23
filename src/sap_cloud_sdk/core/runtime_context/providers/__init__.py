"""Built-in context providers."""

from sap_cloud_sdk.core.runtime_context.providers._headers import HeaderContextProvider
from sap_cloud_sdk.core.runtime_context.providers._ias import (
    GLOBAL_TENANT_ID,
    IASContextProvider,
    TENANT_ID,
    USER_ID,
)

__all__ = [
    "GLOBAL_TENANT_ID",
    "HeaderContextProvider",
    "IASContextProvider",
    "TENANT_ID",
    "USER_ID",
]
