"""Built-in ContextProvider implementations."""

from sap_cloud_sdk.core.runtime_context._context import RequestContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.ias import parse_token


class IASContextProvider(ContextProvider):
    """Extracts tenant/user context from an IAS JWT ``Authorization`` header.

    Reads from a :class:`RequestEnvelope` — works with any framework.

    The following claims are mapped:

      - ``app_tid``        → :attr:`~.RequestContext.tenant_id`
      - ``user_uuid``      → :attr:`~.RequestContext.user_id`
      - ``x-sap-origin``  → :attr:`~.RequestContext.trigger_type`

    Full :class:`~sap_cloud_sdk.ias.IASClaims` are stored under
    ``RequestContext.extras["ias.claims"]`` for modules that need them.
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

        return RequestContext(
            tenant_id=claims.app_tid if claims else None,
            user_id=claims.user_uuid if claims else None,
            trigger_type=origin or None,
            extras={"ias.claims": claims} if claims else {},
        )
