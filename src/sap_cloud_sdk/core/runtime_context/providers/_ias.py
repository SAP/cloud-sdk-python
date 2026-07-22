"""IAS context provider and its typed keys."""

from sap_cloud_sdk.core.runtime_context._context import RequestContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import ContextKey
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.ias import parse_token

TENANT_ID = ContextKey[str]("tenant_id")
USER_ID = ContextKey[str]("user_id")
IAS_CLAIMS = ContextKey["IASClaims"]("ias.claims")  # type: ignore[type-arg]


class IASContextProvider(ContextProvider):
    """Extracts tenant/user context from an IAS JWT ``Authorization`` header.

    Reads from a :class:`~sap_cloud_sdk.core.runtime_context.RequestEnvelope`
    — works with any framework.

    Defines and populates the following context keys:

      - :data:`TENANT_ID`  from ``app_tid`` claim
      - :data:`USER_ID`    from ``user_uuid`` claim
      - :data:`IAS_CLAIMS` full :class:`~sap_cloud_sdk.ias.IASClaims` object
    """

    def extract(self, envelope: RequestEnvelope) -> RequestContext:
        auth = envelope.headers.get("authorization", "")

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

        return RequestContext(values)
