"""Typed context key for RequestContext."""

from typing import Generic, TypeVar

T = TypeVar("T")


class ContextKey(Generic[T]):
    """A typed key for reading and writing values in a :class:`RequestContext`.

    Each provider defines its own keys. The type parameter ensures consumers
    get the right type back from :meth:`RequestContext.get`.

    Example::

        MY_KEY = ContextKey[str]("my_key")

        ctx = RequestContext({MY_KEY: "value"})
        ctx.get(MY_KEY)  # -> "value"
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"ContextKey({self.name!r})"
