"""Starlette/FastAPI middleware for IAS JWT telemetry attribute extraction."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, Dict

from sap_cloud_sdk.core.telemetry.middleware.base import TelemetryMiddleware

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    from sap_cloud_sdk.ias import parse_token
except ImportError as exc:
    raise ImportError(
        "The 'starlette' package is required to use StarletteIASTelemetryMiddleware. "
        "Install it with: pip install starlette"
    ) from exc

logger = logging.getLogger(__name__)

_ATTR_TENANT_ID = "sap.tenancy.tenant_id"
_ATTR_USER_ID = "user.id"


class StarletteIASTelemetryMiddleware(TelemetryMiddleware):
    """Starlette/FastAPI middleware that extracts IAS JWT claims as telemetry attributes.

    Reads the ``Authorization: Bearer <token>`` header on each request,
    parses it as an IAS JWT, and exposes the following as span attributes:
      - ``sap.tenancy.tenant_id`` from the ``app_tid`` claim
      - ``user.id``               from the ``user_uuid`` claim

    If the header is absent or the token cannot be parsed, no attributes are set
    and the request continues normally.

    Each instance owns its own ContextVar so multiple instances on the same app
    do not interfere with each other.

    Usage::

        from starlette.applications import Starlette
        from sap_cloud_sdk.core.telemetry import auto_instrument
        from sap_cloud_sdk.core.telemetry.middleware import StarletteIASTelemetryMiddleware

        app = Starlette(...)
        auto_instrument(middlewares=[StarletteIASTelemetryMiddleware(app=app)])
    """

    def __init__(self, app: Any) -> None:
        """
        Args:
            app: The Starlette application instance.
        """
        self.app = app
        self._attrs_var: ContextVar[Dict[str, Any]] = ContextVar(
            f"ias_attrs_{id(self)}", default={}
        )

    def register(self, app: Any) -> None:
        """Register the IAS JWT middleware with the Starlette app.

        The ``app`` argument is ignored — this implementation always uses
        ``self.app`` provided at construction time.

        Args:
            app: Ignored.
        """
        attrs_var = self._attrs_var

        class _Middleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next: Any) -> Response:
                attrs = _extract_ias_attrs(request)
                token = attrs_var.set(attrs)
                try:
                    return await call_next(request)
                finally:
                    attrs_var.reset(token)

        self.app.add_middleware(_Middleware)
        logger.debug("Registered IAS telemetry middleware on %r", self.app)

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
    if claims.app_tid:
        attrs[_ATTR_TENANT_ID] = claims.sap_gtid
    if claims.user_uuid:
        attrs[_ATTR_USER_ID] = claims.user_uuid
    return attrs
