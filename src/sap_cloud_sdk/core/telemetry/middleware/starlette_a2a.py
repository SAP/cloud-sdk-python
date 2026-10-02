"""Starlette/FastAPI middleware for IAS JWT telemetry attribute extraction."""

import logging
from contextvars import ContextVar
from typing import Any, Dict, Optional, Tuple

from sap_cloud_sdk.core.telemetry.constants import (
    ATTR_SAP_TRIGGER_TYPE,
    ATTR_SAP_TENANT_ID,
    ATTR_USER_ID,
)
from sap_cloud_sdk.core.telemetry.middleware.base import TelemetryMiddleware
from sap_cloud_sdk.ias import IASConfigError, IASVerifier, TokenVerifier, VerifiedIASClaims  # noqa: F401
from sap_cloud_sdk.ias import set_auth_context
from sap_cloud_sdk.ias._token import IASClaims

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
except ImportError as exc:
    raise ImportError(
        "The 'starlette' package is required to use StarletteIASTelemetryMiddleware. "
        "Install it with: pip install starlette"
    ) from exc

logger = logging.getLogger(__name__)


class _IASMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        attrs_var: ContextVar[Dict[str, Any]],
        token_verifier: Optional[TokenVerifier],
    ) -> None:
        super().__init__(app)
        self._attrs_var = attrs_var
        self._token_verifier = token_verifier

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        verified_claims, attrs = _verify_and_extract(request, self._token_verifier)
        set_auth_context(verified_claims)
        token = self._attrs_var.set(attrs)
        try:
            return await call_next(request)
        finally:
            self._attrs_var.reset(token)


class StarletteIASTelemetryMiddleware(TelemetryMiddleware):
    """Starlette/FastAPI middleware that extracts verified IAS JWT claims as telemetry attributes.

    Reads the ``Authorization: Bearer <token>`` header on each request, verifies it using
    a :class:`~sap_cloud_sdk.ias.IASVerifier`, and exposes the following as span attributes
    on success:
      - ``sap.tenancy.tenant_id`` from the ``sap_gtid`` claim
      - ``user.id``               from the ``user_uuid`` claim

    The ``x-sap-origin`` header (trigger type, not JWT identity) is always stamped when
    present, regardless of token verification outcome.

    Verified claims are also stored in the IAS auth context (see
    :func:`~sap_cloud_sdk.ias.get_auth_context`) for downstream use by the AuditClient
    auto-fill. When verification fails, the auth context is set to ``None`` so downstream
    consumers see no identity rather than unverified claims.

    **Auto-configuration (recommended):** when no ``token_verifier`` is supplied, the
    middleware automatically creates an :class:`~sap_cloud_sdk.ias.IASVerifier` from the
    SAP BTP Identity service binding (``VCAP_SERVICES`` on CF, or ``IAS_URL`` env var on
    Kubernetes). If the binding is not found, identity attributes are disabled and a
    WARNING is logged — the app still starts normally.

    Each instance owns its own ContextVar to prevent cross-talk when multiple middleware
    instances are registered on the same app.

    Args:
        app: The Starlette/FastAPI application instance.
        token_verifier: Optional. A callable that receives the raw ``Authorization`` header
            value and returns :class:`~sap_cloud_sdk.ias.VerifiedIASClaims` on success, or
            raises on any invalid token. When ``None`` (default), an
            :class:`~sap_cloud_sdk.ias.IASVerifier` is auto-configured from the environment.

    Usage::

        from starlette.applications import Starlette
        from sap_cloud_sdk.core.telemetry import auto_instrument
        from sap_cloud_sdk.core.telemetry.middleware import StarletteIASTelemetryMiddleware

        app = Starlette(...)
        # Auto-configures from IAS service binding — no extra config needed
        auto_instrument(middlewares=[StarletteIASTelemetryMiddleware(app=app)])
    """

    def __init__(self, app: Any, token_verifier: Optional[TokenVerifier] = None) -> None:
        self.app = app
        if token_verifier is None:
            token_verifier = _auto_configure_verifier()
        self._token_verifier = token_verifier
        self._attrs_var: ContextVar[Dict[str, Any]] = ContextVar(
            f"ias_attrs_{id(self)}", default={}
        )

    def register(self) -> None:
        """Register the IAS JWT middleware with ``self.app``."""
        self.app.add_middleware(
            _IASMiddleware,
            attrs_var=self._attrs_var,
            token_verifier=self._token_verifier,
        )
        logger.info("Registered IAS telemetry middleware on %r", self.app)

    def get_attributes(self) -> Dict[str, Any]:
        """Return IAS JWT attributes extracted from the current request."""
        return self._attrs_var.get()


def _verify_and_extract(
    request: Request, token_verifier: Optional[TokenVerifier]
) -> Tuple[Optional[IASClaims], Dict[str, Any]]:
    """Verify the request token once; return (verified_claims, telemetry_attrs).

    ``x-sap-origin`` is always stamped when present — it is a plain request
    header, not JWT identity data, so it is independent of verification.

    Identity attrs and the returned claims are None/empty when:
    - no Authorization header is present
    - token_verifier is None (fail-closed default)
    - the verifier raises for any reason (bad sig, wrong iss, expired, etc.)
    """
    attrs: Dict[str, Any] = {}

    origin = request.headers.get("x-sap-origin")
    if origin:
        attrs[ATTR_SAP_TRIGGER_TYPE] = origin

    auth = request.headers.get("authorization", "")
    if not auth or token_verifier is None:
        return None, attrs

    try:
        verified = token_verifier(auth)
    except Exception as exc:
        logger.debug("IAS token verification failed, skipping identity attrs: %s", exc)
        return None, attrs

    claims = verified.claims
    if claims.sap_gtid:
        attrs[ATTR_SAP_TENANT_ID] = claims.sap_gtid
    if claims.user_uuid:
        attrs[ATTR_USER_ID] = claims.user_uuid
    return claims, attrs


def _auto_configure_verifier() -> Optional[TokenVerifier]:
    """Try to build an IASVerifier from the environment; warn and return None if not possible."""
    try:
        verifier = IASVerifier.from_env()
        logger.debug(
            "StarletteIASTelemetryMiddleware: auto-configured IASVerifier from environment"
        )
        return verifier
    except IASConfigError as exc:
        logger.warning(
            "StarletteIASTelemetryMiddleware: IAS service binding not found — "
            "sap.tenancy.tenant_id and user.id will NOT be stamped on spans. "
            "Bind an SAP Identity service instance or set IAS_URL to enable "
            "identity attributes. Details: %s",
            exc,
        )
        return None
