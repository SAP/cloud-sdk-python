"""SAP standard headers context provider."""

from sap_cloud_sdk.core.runtime_context._context import RuntimeContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import TRIGGER_TYPE
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider


class HeaderContextProvider(ContextProvider):
    """Extracts context from plain request headers.

    Defines and populates the following context keys:

      - :data:`~sap_cloud_sdk.core.runtime_context.TRIGGER_TYPE`
        from ``x-sap-origin``
    """

    def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
        values = {}
        origin = envelope.headers.get("x-sap-origin")
        if origin:
            values[TRIGGER_TYPE] = origin
        return RuntimeContext(values)
