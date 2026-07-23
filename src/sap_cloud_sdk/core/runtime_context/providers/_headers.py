"""SAP standard headers context provider."""

from typing import Dict

from sap_cloud_sdk.core.runtime_context._context import RuntimeContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import (
    ContextKey,
    DWC_SUBDOMAIN,
    DWC_TENANT,
    TRIGGER_TYPE,
)
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider

_HEADER_MAP: Dict[str, ContextKey[str]] = {
    "x-sap-origin": TRIGGER_TYPE,
    "dwc-subdomain": DWC_SUBDOMAIN,
    "dwc-tenant": DWC_TENANT,
}


class HeaderContextProvider(ContextProvider):
    """Extracts context from plain request headers.

    Defines and populates the following context keys:

      - :data:`~sap_cloud_sdk.core.runtime_context.TRIGGER_TYPE` from ``x-sap-origin``
      - :data:`~sap_cloud_sdk.core.runtime_context.DWC_SUBDOMAIN` from ``dwc-subdomain``
      - :data:`~sap_cloud_sdk.core.runtime_context.DWC_TENANT` from ``dwc-tenant``
    """

    def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
        values = {
            key: value
            for header, key in _HEADER_MAP.items()
            if (value := envelope.headers.get(header))
        }
        return RuntimeContext(values)
