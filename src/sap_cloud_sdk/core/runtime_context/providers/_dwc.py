"""DWC context provider."""

from sap_cloud_sdk.core.runtime_context._context import RuntimeContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import DWC_SUBDOMAIN, DWC_TENANT, FEATURE_TOGGLES
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider

_FEATURE_TOGGLES_HEADER = "dwc-feature-toggles"


class DWCContextProvider(ContextProvider):
    """Extracts DWC tenant context from SAP DWC request headers.

    Defines and populates the following context keys:

      - :data:`~sap_cloud_sdk.core.runtime_context.DWC_SUBDOMAIN` from ``dwc-subdomain``
      - :data:`~sap_cloud_sdk.core.runtime_context.DWC_TENANT` from ``dwc-tenant``
      - :data:`~sap_cloud_sdk.core.runtime_context.FEATURE_TOGGLES` from ``dwc-feature-toggles``
    """

    def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
        values = {}
        if subdomain := envelope.headers.get("dwc-subdomain"):
            values[DWC_SUBDOMAIN] = subdomain
        if tenant := envelope.headers.get("dwc-tenant"):
            values[DWC_TENANT] = tenant
        if raw := envelope.headers.get(_FEATURE_TOGGLES_HEADER):
            values[FEATURE_TOGGLES] = [t.strip() for t in raw.split(",") if t.strip()]
        return RuntimeContext(values)
