"""Starlette/FastAPI middleware for IAS JWT telemetry attribute extraction."""

import logging
from contextvars import ContextVar
from typing import Any, Dict

from sap_cloud_sdk.core.telemetry.constants import (
    ATTR_SAP_TRIGGER_TYPE,
    ATTR_SAP_TENANT_ID,
    ATTR_USER_ID,
)
from sap_cloud_sdk.core.telemetry.middleware.base import TelemetryMiddleware
from sap_cloud_sdk.ias import parse_token

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
    def __init__(self, app: Any, attrs_var: ContextVar[Dict[str, Any]]) -> None:
        super().__init__(app)
        self._attrs_var = attrs_var

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        token = self._attrs_var.set(_extract_ias_attrs(request))
        try:
            return await call_next(request)
        finally:
            self._attrs_var.reset(token)


class StarletteIASTelemetryMiddleware(TelemetryMiddleware):
    """Starlette/FastAPI middleware that extracts IAS JWT claims as telemetry attributes.

    Reads the ``Authorization: Bearer <token>`` header on each request,
    parses it as an IAS JWT, and exposes the following as span attributes:
      - ``sap.tenancy.tenant_id`` from the ``sap_gtid`` claim
      - ``user.id``               from the ``user_uuid`` claim

    If the header is absent or the token cannot be parsed, no attributes are set
    and the request continues normally.

    Each instance owns its own ContextVar to prevent cross-talk when multiple
    middleware instances are registered on the same app.

    Usage::

        from starlette.applications import Starlette
        from sap_cloud_sdk.core.telemetry import auto_instrument
        from sap_cloud_sdk.core.telemetry.middleware import StarletteIASTelemetryMiddleware

        app = Starlette(...)
        auto_instrument(middlewares=[StarletteIASTelemetryMiddleware(app=app)])
    """

    def __init__(self, app: Any) -> None:
        self.app = app
        self._attrs_var: ContextVar[Dict[str, Any]] = ContextVar(
            f"ias_attrs_{id(self)}", default={}
        )

    def register(self) -> None:
        """Register the IAS JWT middleware with ``self.app``."""
        self.app.add_middleware(_IASMiddleware, attrs_var=self._attrs_var)
        logger.info("Registered IAS telemetry middleware on %r", self.app)

    def get_attributes(self) -> Dict[str, Any]:
        """Return IAS JWT attributes extracted from the current request."""
        return self._attrs_var.get()


def _extract_ias_attrs(request: Request) -> Dict[str, Any]:
    """Parse the Authorization header and return telemetry attributes."""
    auth = request.headers.get("authorization", "")
    if not auth:
        return {}
    try:
        claims = parse_token(auth)
    except Exception as e:
        logger.debug("IAS token parsing failed, skipping telemetry attrs: %s", e)
        return {}

    attrs: Dict[str, Any] = {}
    if claims.sap_gtid:
        attrs[ATTR_SAP_TENANT_ID] = claims.sap_gtid
    if claims.user_uuid:
        attrs[ATTR_USER_ID] = claims.user_uuid
    origin = request.headers.get("x-sap-origin")
    if origin:
        attrs[ATTR_SAP_TRIGGER_TYPE] = origin
    return attrs
