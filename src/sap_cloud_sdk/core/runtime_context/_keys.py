"""Typed context key for RuntimeContext."""

from typing import Generic, TypeVar

T = TypeVar("T")


class ContextKey(Generic[T]):
    """A typed key for reading and writing values in a :class:`RuntimeContext`.

    Each provider defines its own keys. The type parameter ensures consumers
    get the right type back from :meth:`RuntimeContext.get`.

    Keys use object identity for lookup — two ``ContextKey`` instances with the
    same name are **different keys**. Always import the canonical key from the
    module that defined it; never create a second instance with the same name.

    Example::

        MY_KEY = ContextKey[str]("my_key")

        ctx = RuntimeContext({MY_KEY: "value"})
        ctx.get(MY_KEY)  # -> "value"

        other = ContextKey[str]("my_key")
        ctx.get(other)   # -> None  (different key object)
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"ContextKey({self.name!r})"


# SDK-standard keys — not tied to any specific auth provider.
TRIGGER_TYPE = ContextKey[str]("trigger_type")
DWC_SUBDOMAIN = ContextKey[str]("dwc_subdomain")
DWC_TENANT = ContextKey[str]("dwc_tenant")
