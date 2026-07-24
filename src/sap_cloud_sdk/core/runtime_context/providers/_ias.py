"""IAS context provider and its typed keys."""

import logging

from sap_cloud_sdk.core.runtime_context._context import RuntimeContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import ContextKey
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.ias import parse_token

logger = logging.getLogger(__name__)

TENANT_ID = ContextKey[str]("ias.app_tid")
GLOBAL_TENANT_ID = ContextKey[str]("ias.sap_gtid")
USER_ID = ContextKey[str]("ias.user_uuid")


class IASContextProvider(ContextProvider):
    """Extracts tenant/user context from an IAS JWT ``Authorization`` header.

    Reads from a :class:`~sap_cloud_sdk.core.runtime_context.RequestEnvelope`
    — works with any framework.

    Defines and populates the following context keys:

      - :data:`TENANT_ID`        from ``app_tid`` claim
      - :data:`GLOBAL_TENANT_ID` from ``sap_gtid`` claim
      - :data:`USER_ID`          from ``user_uuid`` claim
    """

    def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
        auth = envelope.headers.get("authorization", "")

        claims = None
        if auth:
            try:
                claims = parse_token(auth)
            except Exception as e:
                logger.debug("IAS token parsing failed, context will be empty: %s", e)

        values = {}
        if claims:
            if claims.app_tid:
                values[TENANT_ID] = claims.app_tid
            if claims.sap_gtid:
                values[GLOBAL_TENANT_ID] = claims.sap_gtid
            if claims.user_uuid:
                values[USER_ID] = claims.user_uuid

        return RuntimeContext(values)
