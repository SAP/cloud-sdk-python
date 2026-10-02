"""Starlette/FastAPI middleware for IAS JWT telemetry attribute extraction."""

import logging
from contextvars import ContextVar
from typing import Any, Dict, Optional

from sap_cloud_sdk.core.telemetry.constants import (
    ATTR_SAP_TRIGGER_TYPE,
    ATTR_SAP_TENANT_ID,
    ATTR_USER_ID,
)
from sap_cloud_sdk.core.telemetry.middleware.base import TelemetryMiddleware
from sap_cloud_sdk.ias import TokenVerifier, VerifiedIASClaims  # noqa: F401

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
        token = self._attrs_var.set(_extract_ias_attrs(request, self._token_verifier))
        try:
            return await call_next(request)
        finally:
            self._attrs_var.reset(token)


class StarletteIASTelemetryMiddleware(TelemetryMiddleware):
    """Starlette/FastAPI middleware that extracts verified IAS JWT claims as telemetry attributes.

    Reads the ``Authorization: Bearer <token>`` header on each request, passes it through
    the provided ``token_verifier``, and exposes the following as span attributes on success:
      - ``sap.tenancy.tenant_id`` from the ``sap_gtid`` claim
      - ``user.id``               from the ``user_uuid`` claim

    The ``x-sap-origin`` header (trigger type, not JWT identity) is always stamped when
    present, regardless of token verification outcome.

    If ``token_verifier`` is ``None`` (the default), **no identity attributes are stamped**
    and a warning is logged once at construction. This is a safe default — the app runs
    normally but ``sap.tenancy.tenant_id`` and ``user.id`` will be absent from spans until
    a verifier is supplied. See the IAS user guide for how to implement a verifier.

    If the verifier raises for any reason (bad signature, wrong issuer, expired token,
    unknown algorithm, etc.), the identity attributes are silently omitted and the request
    continues normally.

    Each instance owns its own ContextVar to prevent cross-talk when multiple middleware
    instances are registered on the same app.

    Args:
        app: The Starlette/FastAPI application instance.
        token_verifier: A callable that receives the raw ``Authorization`` header value
            and returns a :class:`~sap_cloud_sdk.ias.VerifiedIASClaims` on success, or
            raises on any invalid token. If ``None``, identity attributes are disabled.

    Usage::

        from starlette.applications import Starlette
        from sap_cloud_sdk.core.telemetry import auto_instrument
        from sap_cloud_sdk.core.telemetry.middleware import StarletteIASTelemetryMiddleware
        from sap_cloud_sdk.ias import VerifiedIASClaims, parse_token

        def my_verifier(authorization: str) -> VerifiedIASClaims:
            # Your platform (e.g. Kyma Istio) already verified the JWT.
            # See the IAS user guide for a full JWKS-based verifier example.
            return VerifiedIASClaims(claims=parse_token(authorization))

        app = Starlette(...)
        auto_instrument(middlewares=[StarletteIASTelemetryMiddleware(app=app, token_verifier=my_verifier)])
    """

    def __init__(self, app: Any, token_verifier: Optional[TokenVerifier] = None) -> None:
        self.app = app
        self._token_verifier = token_verifier
        self._attrs_var: ContextVar[Dict[str, Any]] = ContextVar(
            f"ias_attrs_{id(self)}", default={}
        )
        if token_verifier is None:
            logger.warning(
                "StarletteIASTelemetryMiddleware: no token_verifier supplied — "
                "sap.tenancy.tenant_id and user.id will NOT be stamped on spans. "
                "Supply a token_verifier to enable verified IAS identity attributes. "
                "See the IAS user guide for a JWKS-based verifier example."
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


def _extract_ias_attrs(
    request: Request, token_verifier: Optional[TokenVerifier]
) -> Dict[str, Any]:
    """Extract telemetry attributes from the request.

    ``x-sap-origin`` (trigger type) is always included when present — it is a plain
    request header, not JWT identity data.

    Identity attributes (``sap.tenancy.tenant_id``, ``user.id``) are included only when
    ``token_verifier`` is provided and succeeds for the ``Authorization`` header.
    """
    attrs: Dict[str, Any] = {}

    # x-sap-origin is not JWT identity — stamp it regardless of verification outcome.
    origin = request.headers.get("x-sap-origin")
    if origin:
        attrs[ATTR_SAP_TRIGGER_TYPE] = origin

    auth = request.headers.get("authorization", "")
    if not auth:
        return attrs

    if token_verifier is None:
        return attrs  # fail-closed for identity; warned once at construction

    try:
        verified = token_verifier(auth)
    except Exception as e:
        logger.debug("IAS token verification failed, skipping identity attrs: %s", e)
        return attrs

    claims = verified.claims
    if claims.sap_gtid:
        attrs[ATTR_SAP_TENANT_ID] = claims.sap_gtid
    if claims.user_uuid:
        attrs[ATTR_USER_ID] = claims.user_uuid
    return attrs
