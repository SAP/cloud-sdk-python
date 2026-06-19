"""Generic CRUD request builder classes for OData v4."""

from __future__ import annotations

import dataclasses
from typing import Any, Generic, Iterator, TypeVar, TYPE_CHECKING

from sap_cloud_sdk.core.odata._query import OrderDirection, StructuredQuery
from sap_cloud_sdk.core.odata._response import deserialize_collection, deserialize_single
from sap_cloud_sdk.core.odata._pagination import ODataPageIterator

if TYPE_CHECKING:
    from sap_cloud_sdk.core.odata._filter import FilterExpression
    from sap_cloud_sdk.core.odata._transport import ODataHttpTransport

T = TypeVar("T")


def _entity_set_path(entity_type: type) -> str:
    """Return the OData entity-set path for *entity_type*.

    Reads ``entity_type._entity_set`` when present; otherwise defaults to
    the class name (common for generated types).
    """
    return getattr(entity_type, "_entity_set", None) or entity_type.__name__


def _build_key_segment(key: dict[str, Any]) -> str:
    """Serialise *key* dict to an OData key segment, e.g. ``(ID='x',Ver=1)``."""
    from sap_cloud_sdk.core.odata._filter import _format_value

    if len(key) == 1:
        return f"({_format_value(next(iter(key.values())))})"
    parts = ",".join(f"{k}={_format_value(v)}" for k, v in key.items())
    return f"({parts})"


class GetAllRequestBuilder(Generic[T]):
    """Fluent builder for OData collection (GetAll) requests.

    Example::

        results = (
            GetAllRequestBuilder(transport, BusinessPartner)
            .select("BusinessPartnerID", "DisplayName")
            .filter(FilterExpression.field("DisplayName").contains("Acme"))
            .top(50)
            .execute()
        )
    """

    def __init__(
        self, transport: "ODataHttpTransport", entity_type: type[T]
    ) -> None:
        self._transport = transport
        self._entity_type = entity_type
        self._query = StructuredQuery()

    def select(self, *fields: str) -> "GetAllRequestBuilder[T]":
        self._query = self._query.select(*fields)
        return self

    def filter(self, expression: "FilterExpression") -> "GetAllRequestBuilder[T]":
        self._query = self._query.filter(expression)
        return self

    def order_by(
        self,
        field_name: str,
        direction: OrderDirection = OrderDirection.ASC,
    ) -> "GetAllRequestBuilder[T]":
        self._query = self._query.order_by(field_name, direction)
        return self

    def top(self, n: int) -> "GetAllRequestBuilder[T]":
        self._query = self._query.top(n)
        return self

    def skip(self, n: int) -> "GetAllRequestBuilder[T]":
        self._query = self._query.skip(n)
        return self

    def expand(self, *nav_properties: str) -> "GetAllRequestBuilder[T]":
        self._query = self._query.expand(*nav_properties)
        return self

    def execute(self) -> list[T]:
        """Execute the request and return all matching entities."""
        path = _entity_set_path(self._entity_type)
        data = self._transport.get(path, params=self._query.to_params())
        return deserialize_collection(data, self._entity_type)

    def iterate_pages(self) -> Iterator[list[T]]:
        """Yield pages using server-driven pagination (``@odata.nextLink``)."""
        path = _entity_set_path(self._entity_type)
        first_url = self._transport.absolute_url(path)
        params = self._query.to_params()
        if params:
            from urllib.parse import urlencode
            first_url += "?" + urlencode(params)

        def _fetch(url: str) -> dict[str, Any]:
            return self._transport.get(url.replace(self._transport._base_url + "/", ""))

        iterator = ODataPageIterator(
            fetch_page=lambda url: self._transport._request("GET", _strip_base(url, self._transport._base_url)),
            entity_type=self._entity_type,
            first_url=first_url,
        )
        yield from iterator

    def iterate_entities(self) -> Iterator[T]:
        """Yield individual entities across all pages."""
        for page in self.iterate_pages():
            yield from page


def _strip_base(url: str, base_url: str) -> str:
    """Strip *base_url* prefix from *url* to get a relative path."""
    prefix = base_url + "/"
    if url.startswith(prefix):
        return url[len(prefix):]
    return url


class GetByKeyRequestBuilder(Generic[T]):
    """Fluent builder for a single-entity (GetByKey) request."""

    def __init__(
        self,
        transport: "ODataHttpTransport",
        entity_type: type[T],
        key: dict[str, Any],
    ) -> None:
        self._transport = transport
        self._entity_type = entity_type
        self._key = key
        self._query = StructuredQuery()

    def select(self, *fields: str) -> "GetByKeyRequestBuilder[T]":
        self._query = self._query.select(*fields)
        return self

    def expand(self, *nav_properties: str) -> "GetByKeyRequestBuilder[T]":
        self._query = self._query.expand(*nav_properties)
        return self

    def execute(self) -> T:
        """Fetch the entity, raising :exc:`ODataNotFoundError` if absent."""
        path = _entity_set_path(self._entity_type) + _build_key_segment(self._key)
        data = self._transport.get(path, params=self._query.to_params())
        return deserialize_single(data, self._entity_type)


class CreateRequestBuilder(Generic[T]):
    """Builder for OData entity creation (POST)."""

    def __init__(
        self, transport: "ODataHttpTransport", entity: T
    ) -> None:
        self._transport = transport
        self._entity = entity

    def execute(self) -> T:
        """Create the entity and return the server response as the same type."""
        entity_type = type(self._entity)
        path = _entity_set_path(entity_type)
        body = self._entity.to_dict() if hasattr(self._entity, "to_dict") else dataclasses.asdict(self._entity)  # type: ignore[arg-type]
        data = self._transport.post(path, body)
        return deserialize_single(data, entity_type)


class UpdateRequestBuilder(Generic[T]):
    """Builder for OData entity update (PATCH by default, PUT when ``.replace()`` called)."""

    def __init__(
        self,
        transport: "ODataHttpTransport",
        entity: T,
        etag: str | None = None,
    ) -> None:
        self._transport = transport
        self._entity = entity
        self._use_put = False
        self._etag = etag

    def replace(self) -> "UpdateRequestBuilder[T]":
        """Switch from PATCH (default) to PUT (full replacement)."""
        self._use_put = True
        return self

    def execute(self) -> T:
        """Send the update and return the server response."""
        entity_type = type(self._entity)
        key_fields: list[str] = getattr(entity_type, "_key_fields", [])
        if not key_fields:
            raise ValueError(
                f"{entity_type.__name__} does not define _key_fields; "
                "cannot build a key path for update"
            )
        key = {k: getattr(self._entity, k) for k in key_fields}
        path = _entity_set_path(entity_type) + _build_key_segment(key)
        body = self._entity.to_dict() if hasattr(self._entity, "to_dict") else dataclasses.asdict(self._entity)  # type: ignore[arg-type]
        if self._use_put:
            data = self._transport.put(path, body, etag=self._etag)
        else:
            data = self._transport.patch(path, body, etag=self._etag)
        if not data:
            return self._entity
        return deserialize_single(data, entity_type)


class DeleteRequestBuilder(Generic[T]):
    """Builder for OData entity deletion (DELETE)."""

    def __init__(
        self,
        transport: "ODataHttpTransport",
        entity_type: type[T],
        key: dict[str, Any],
        etag: str | None = None,
    ) -> None:
        self._transport = transport
        self._entity_type = entity_type
        self._key = key
        self._etag = etag

    def execute(self) -> None:
        """Delete the entity."""
        path = _entity_set_path(self._entity_type) + _build_key_segment(self._key)
        self._transport.delete(path, etag=self._etag)
