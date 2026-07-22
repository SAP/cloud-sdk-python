"""Typed context key for RuntimeContext."""

from typing import Generic, TypeVar

T = TypeVar("T")


class ContextKey(Generic[T]):
    """A typed key for reading and writing values in a :class:`RuntimeContext`.

    Each provider defines its own keys. The type parameter ensures consumers
    get the right type back from :meth:`RuntimeContext.get`.

    Example::

        MY_KEY = ContextKey[str]("my_key")

        ctx = RuntimeContext({MY_KEY: "value"})
        ctx.get(MY_KEY)  # -> "value"
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"ContextKey({self.name!r})"


# SDK-standard keys — not tied to any specific auth provider.
TRIGGER_TYPE = ContextKey[str]("trigger_type")
