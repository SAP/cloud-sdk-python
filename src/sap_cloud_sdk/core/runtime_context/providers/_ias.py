"""IAS context provider and its typed keys."""

import logging
from typing import Optional

from sap_cloud_sdk.core.runtime_context._context import RuntimeContext
from sap_cloud_sdk.core.runtime_context._envelope import RequestEnvelope
from sap_cloud_sdk.core.runtime_context._keys import ContextKey
from sap_cloud_sdk.core.runtime_context._protocol import ContextProvider
from sap_cloud_sdk.ias import IASConfigError, IASVerifier, TokenVerifier

logger = logging.getLogger(__name__)

APP_TENANT_ID = ContextKey[str]("ias.app_tid")
GLOBAL_TENANT_ID = ContextKey[str]("ias.sap_gtid")
USER_ID = ContextKey[str]("ias.user_uuid")


def _auto_configure_verifier() -> Optional[TokenVerifier]:
    """Try to build an IASVerifier from the environment; warn and return None if not possible."""
    try:
        verifier = IASVerifier.from_env()
        logger.debug("IASContextProvider: auto-configured IASVerifier from environment")
        return verifier
    except IASConfigError as exc:
        logger.warning(
            "IASContextProvider: IAS service binding not found — "
            "APP_TENANT_ID, GLOBAL_TENANT_ID, and USER_ID will not be populated. "
            "Bind an SAP Identity service instance or set IAS_URL to enable "
            "identity context. Details: %s",
            exc,
        )
        return None


class IASContextProvider(ContextProvider):
    """Extracts tenant/user context from an IAS JWT ``Authorization`` header.

    Reads from a :class:`~sap_cloud_sdk.core.runtime_context.RequestEnvelope`
    — works with any framework.

    Defines and populates the following context keys:

      - :data:`APP_TENANT_ID`    from ``app_tid`` claim
      - :data:`GLOBAL_TENANT_ID` from ``sap_gtid`` claim
      - :data:`USER_ID`          from ``user_uuid`` claim

    The JWT signature is verified using an :class:`~sap_cloud_sdk.ias.IASVerifier`
    before any claims are trusted. When no ``token_verifier`` is supplied, one is
    auto-configured from the environment (VCAP_SERVICES → K8s secret mount →
    ``IAS_URL`` env var). If no IAS binding is found, a WARNING is logged and the
    provider returns an empty context for every request (fail-closed).

    Args:
        token_verifier: Optional callable that verifies an IAS JWT and returns
            :class:`~sap_cloud_sdk.ias.VerifiedIASClaims`. When ``None``,
            auto-configuration from the environment is attempted.
    """

    def __init__(self, token_verifier: Optional[TokenVerifier] = None) -> None:
        if token_verifier is None:
            token_verifier = _auto_configure_verifier()
        self._token_verifier = token_verifier

    def extract(self, envelope: RequestEnvelope) -> RuntimeContext:
        auth = envelope.headers.get("authorization", "")
        if not auth or self._token_verifier is None:
            return RuntimeContext()
        try:
            verified = self._token_verifier(auth)
        except Exception as e:
            logger.debug("IAS token verification failed, context will be empty: %s", e)
            return RuntimeContext()
        claims = verified.claims
        values = {}
        if claims.app_tid:
            values[APP_TENANT_ID] = claims.app_tid
        if claims.sap_gtid:
            values[GLOBAL_TENANT_ID] = claims.sap_gtid
        if claims.user_uuid:
            values[USER_ID] = claims.user_uuid
        return RuntimeContext(values)
