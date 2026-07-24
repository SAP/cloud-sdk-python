"""SAP trigger type context provider."""

from sap_cloud_sdk.core.runtime_context._context import RuntimeContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import TRIGGER_TYPE
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider


class SAPTriggerContextProvider(ContextProvider):
    """Extracts the SAP trigger type from the ``x-sap-origin`` header.

    Defines and populates the following context key:

      - :data:`~sap_cloud_sdk.core.runtime_context.TRIGGER_TYPE` from ``x-sap-origin``
    """

    def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
        origin = envelope.headers.get("x-sap-origin")
        return RuntimeContext({TRIGGER_TYPE: origin} if origin else {})
