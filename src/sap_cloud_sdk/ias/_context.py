"""Per-request IAS auth context via ContextVar."""

from contextvars import ContextVar
from typing import Optional

from sap_cloud_sdk.ias._token import IASClaims

_auth_context_var: ContextVar[Optional[IASClaims]] = ContextVar(
    "ias_auth_context", default=None
)


def set_auth_context(claims: Optional[IASClaims]) -> None:
    """Store IAS claims for the current async context."""
    _auth_context_var.set(claims)


def get_auth_context() -> Optional[IASClaims]:
    """Return the IAS claims set for the current async context, or None."""
    return _auth_context_var.get()
