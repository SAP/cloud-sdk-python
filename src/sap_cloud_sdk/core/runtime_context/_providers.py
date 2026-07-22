"""Built-in ContextProvider implementations."""

from sap_cloud_sdk.core.runtime_context._context import RequestContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import ContextKey
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.ias import parse_token

# IAS-owned context keys
TENANT_ID = ContextKey[str]("tenant_id")
USER_ID = ContextKey[str]("user_id")
TRIGGER_TYPE = ContextKey[str]("trigger_type")
IAS_CLAIMS = ContextKey["IASClaims"]("ias.claims")  # type: ignore[type-arg]


class IASContextProvider(ContextProvider):
    """Extracts tenant/user context from an IAS JWT ``Authorization`` header.

    Reads from a :class:`RequestEnvelope` — works with any framework.

    Defines and populates the following context keys:

      - :data:`TENANT_ID`    from ``app_tid`` claim
      - :data:`USER_ID`      from ``user_uuid`` claim
      - :data:`TRIGGER_TYPE` from ``x-sap-origin`` header
      - :data:`IAS_CLAIMS`   full :class:`~sap_cloud_sdk.ias.IASClaims` object
    """

    def extract(self, envelope: RequestEnvelope) -> RequestContext:
        auth = envelope.headers.get("authorization", "")
        origin = envelope.headers.get("x-sap-origin")

        claims = None
        if auth:
            try:
                claims = parse_token(auth)
            except Exception:
                pass

        values = {}
        if claims:
            if claims.app_tid:
                values[TENANT_ID] = claims.app_tid
            if claims.user_uuid:
                values[USER_ID] = claims.user_uuid
            values[IAS_CLAIMS] = claims
        if origin:
            values[TRIGGER_TYPE] = origin

        return RequestContext(values)
