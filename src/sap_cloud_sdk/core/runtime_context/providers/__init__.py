"""Built-in context providers."""

from sap_cloud_sdk.core.runtime_context.providers._dwc import DWCContextProvider
from sap_cloud_sdk.core.runtime_context.providers._ias import (
    GLOBAL_TENANT_ID,
    IASContextProvider,
    TENANT_ID,
    USER_ID,
)
from sap_cloud_sdk.core.runtime_context.providers._sap_trigger import (
    SAPTriggerContextProvider,
)

__all__ = [
    "DWCContextProvider",
    "GLOBAL_TENANT_ID",
    "IASContextProvider",
    "SAPTriggerContextProvider",
    "TENANT_ID",
    "USER_ID",
]
