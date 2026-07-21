"""ContextVar backing store for the SDK runtime context."""

from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, Generator, Optional


@dataclass
class RequestContext:
    """Caller-identity snapshot for the current request.

    Attributes:
        tenant_id:    Tenant identifier.
        user_id:      User identifier.
        trigger_type: Origin of the request (e.g. from ``x-sap-origin``).
        extras:       Arbitrary additional data keyed by string.
    """

    tenant_id: Optional[str] = field(default=None)
    user_id: Optional[str] = field(default=None)
    trigger_type: Optional[str] = field(default=None)
    extras: Dict[str, Any] = field(default_factory=dict)


_EMPTY = RequestContext()

_context_var: ContextVar[RequestContext] = ContextVar(
    "sap_sdk_request_context", default=_EMPTY
)


def set_context(ctx: RequestContext) -> None:
    """Set the runtime context for the current async/thread scope."""
    _context_var.set(ctx)


def get_context() -> RequestContext:
    """Return the runtime context for the current async/thread scope.

    Returns an empty :class:`RequestContext` (all fields ``None``) when no
    context has been set.
    """
    return _context_var.get()


@contextmanager
def sdk_context(ctx: RequestContext) -> Generator[RequestContext, None, None]:
    """Sync context manager that sets *ctx* for the duration of the block."""
    token = _context_var.set(ctx)
    try:
        yield ctx
    finally:
        _context_var.reset(token)


@asynccontextmanager
async def async_sdk_context(
    ctx: RequestContext,
) -> AsyncGenerator[RequestContext, None]:
    """Async context manager that sets *ctx* for the duration of the block."""
    token = _context_var.set(ctx)
    try:
        yield ctx
    finally:
        _context_var.reset(token)
