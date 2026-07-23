"""ContextVar backing store for the SDK runtime context."""

from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any, AsyncGenerator, Dict, Generator, Optional, TypeVar

from sap_cloud_sdk.core.runtime_context._keys import ContextKey

T = TypeVar("T")


class RuntimeContext:
    """Immutable typed bag of caller-identity values for the current execution.

    Values are keyed by :class:`ContextKey` instances, which carry the
    expected type. Use :meth:`get` to read a value and :meth:`with_value`
    to produce a new context with an additional entry.

    Example::

        MY_KEY = ContextKey[str]("my_key")

        ctx = RuntimeContext({MY_KEY: "hello"})
        ctx.get(MY_KEY)  # -> "hello"
    """

    def __init__(self, values: Optional[Dict[ContextKey, Any]] = None) -> None:
        self._values: Dict[ContextKey, Any] = dict(values) if values else {}

    def get(self, key: ContextKey[T]) -> Optional[T]:
        """Return the value for *key*, or ``None`` if not set."""
        return self._values.get(key)

    def with_value(self, key: ContextKey[T], value: T) -> "RuntimeContext":
        """Return a new RuntimeContext with *key* set to *value*."""
        return RuntimeContext({**self._values, key: value})

    def _raw(self) -> Dict[ContextKey, Any]:
        """Return a shallow copy of the internal values dict."""
        return dict(self._values)

    def __repr__(self) -> str:
        pairs = ", ".join(f"{k.name}={v!r}" for k, v in self._values.items())
        return f"RuntimeContext({{{pairs}}})"


_EMPTY = RuntimeContext()

_context_var: ContextVar[RuntimeContext] = ContextVar(
    "sap_sdk_request_context", default=_EMPTY
)


def set_context(ctx: RuntimeContext) -> None:
    """Set the runtime context for the current async/thread scope."""
    _context_var.set(ctx)


def get_context() -> RuntimeContext:
    """Return the runtime context for the current async/thread scope.

    Returns an empty :class:`RuntimeContext` when no context has been set.
    """
    return _context_var.get()


@contextmanager
def sdk_context(ctx: RuntimeContext) -> Generator[RuntimeContext, None, None]:
    """Sync context manager that sets *ctx* for the duration of the block."""
    token = _context_var.set(ctx)
    try:
        yield ctx
    finally:
        _context_var.reset(token)


@asynccontextmanager
async def async_sdk_context(
    ctx: RuntimeContext,
) -> AsyncGenerator[RuntimeContext, None]:
    """Async context manager that sets *ctx* for the duration of the block."""
    token = _context_var.set(ctx)
    try:
        yield ctx
    finally:
        _context_var.reset(token)
