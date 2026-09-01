"""DWC context provider."""

import base64
import json
import logging

from sap_cloud_sdk.core.runtime_context._context import RuntimeContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import (
    DWC_SUBDOMAIN,
    DWC_TENANT,
    FEATURE_TOGGLES,
)
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider

logger = logging.getLogger(__name__)

_FEATURE_TOGGLES_HEADER = "dwc-stage-configuration"


class DWCContextProvider(ContextProvider):
    """Extracts DWC tenant context from SAP DWC request headers.

    Defines and populates the following context keys:

      - :data:`~sap_cloud_sdk.core.runtime_context.DWC_SUBDOMAIN` from ``dwc-subdomain``
      - :data:`~sap_cloud_sdk.core.runtime_context.DWC_TENANT` from ``dwc-tenant``
      - :data:`~sap_cloud_sdk.core.runtime_context.FEATURE_TOGGLES` from ``dwc-stage-configuration``
    """

    def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
        values = {}
        if subdomain := envelope.headers.get("dwc-subdomain"):
            values[DWC_SUBDOMAIN] = subdomain
        if tenant := envelope.headers.get("dwc-tenant"):
            values[DWC_TENANT] = tenant
        if raw := envelope.headers.get(_FEATURE_TOGGLES_HEADER):
            toggles = _parse_feature_toggles(raw)
            if toggles is not None:
                values[FEATURE_TOGGLES] = toggles
        return RuntimeContext(values)


def _parse_feature_toggles(raw: str) -> list[str] | None:
    try:
        decoded = base64.b64decode(raw).decode()
        data = json.loads(decoded)
        toggles = [f["name"] for f in data.get("features", []) if f.get("enabled")]
        logger.debug("Feature toggles from dwc-stage-configuration: %s", toggles)
        return toggles
    except Exception as e:
        logger.debug("Failed to parse dwc-stage-configuration header: %s", e)
        return None
