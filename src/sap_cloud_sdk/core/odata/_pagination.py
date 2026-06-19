"""Server-driven pagination via @odata.nextLink."""

from __future__ import annotations

from typing import Any, Callable, Generic, Iterator, TypeVar

from sap_cloud_sdk.core.odata._response import deserialize_collection, next_link

T = TypeVar("T")


class ODataPageIterator(Generic[T]):
    """Lazily yields pages of entities by following ``@odata.nextLink``.

    Args:
        fetch_page: Callable that takes an absolute URL and returns a raw
            JSON dict (the full OData collection response).
        entity_type: Dataclass to deserialize each item into.
        first_url: The initial request URL (already including query params).
    """

    def __init__(
        self,
        fetch_page: Callable[[str], dict[str, Any]],
        entity_type: type[T],
        first_url: str,
    ) -> None:
        self._fetch_page = fetch_page
        self._entity_type = entity_type
        self._first_url = first_url

    def __iter__(self) -> Iterator[list[T]]:
        url: str | None = self._first_url
        while url is not None:
            data = self._fetch_page(url)
            yield deserialize_collection(data, self._entity_type)
            url = next_link(data)

    def entities(self) -> Iterator[T]:
        """Yield individual entities across all pages."""
        for page in self:
            yield from page
