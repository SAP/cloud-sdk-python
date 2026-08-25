"""Built-in context providers."""

from sap_cloud_sdk.core.runtime_context.providers._dwc import DWCContextProvider
from sap_cloud_sdk.core.runtime_context.providers._ias import (
    APP_TENANT_ID,
    GLOBAL_TENANT_ID,
    IASContextProvider,
    USER_ID,
)
from sap_cloud_sdk.core.runtime_context.providers._sap_trigger import (
    SAPTriggerContextProvider,
)

__all__ = [
    "APP_TENANT_ID",
    "DWCContextProvider",
    "GLOBAL_TENANT_ID",
    "IASContextProvider",
    "SAPTriggerContextProvider",
    "USER_ID",
]
