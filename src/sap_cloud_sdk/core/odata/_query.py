"""Immutable OData v4 query parameter builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from sap_cloud_sdk.core.odata._constants import (
    QUERY_EXPAND,
    QUERY_FILTER,
    QUERY_ORDERBY,
    QUERY_SELECT,
    QUERY_SKIP,
    QUERY_TOP,
)

if TYPE_CHECKING:
    from ._filter import FilterExpression


class OrderDirection(Enum):
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class StructuredQuery:
    """Immutable OData v4 query parameter builder.

    Every mutating method returns a new instance — safe to share a base query
    across multiple requests::

        base = StructuredQuery().select("ID", "Name").top(50)
        page1 = base.skip(0)
        page2 = base.skip(50)
        page1.to_params()
        # {"$select": "ID,Name", "$top": "50", "$skip": "0"}
    """

    _select: tuple[str, ...] = field(default=(), compare=True)
    _filter: "FilterExpression | None" = field(default=None, compare=True)
    _orderby: tuple[tuple[str, OrderDirection], ...] = field(default=(), compare=True)
    _top: int | None = field(default=None, compare=True)
    _skip: int | None = field(default=None, compare=True)
    _expand: tuple[str, ...] = field(default=(), compare=True)
    _custom: tuple[tuple[str, str], ...] = field(default=(), compare=True)

    def select(self, *fields: str) -> "StructuredQuery":
        return StructuredQuery(
            _select=tuple(fields),
            _filter=self._filter,
            _orderby=self._orderby,
            _top=self._top,
            _skip=self._skip,
            _expand=self._expand,
            _custom=self._custom,
        )

    def filter(self, expression: "FilterExpression") -> "StructuredQuery":
        return StructuredQuery(
            _select=self._select,
            _filter=expression,
            _orderby=self._orderby,
            _top=self._top,
            _skip=self._skip,
            _expand=self._expand,
            _custom=self._custom,
        )

    def order_by(
        self, field_name: str, direction: OrderDirection = OrderDirection.ASC
    ) -> "StructuredQuery":
        return StructuredQuery(
            _select=self._select,
            _filter=self._filter,
            _orderby=self._orderby + ((field_name, direction),),
            _top=self._top,
            _skip=self._skip,
            _expand=self._expand,
            _custom=self._custom,
        )

    def top(self, n: int) -> "StructuredQuery":
        return StructuredQuery(
            _select=self._select,
            _filter=self._filter,
            _orderby=self._orderby,
            _top=n,
            _skip=self._skip,
            _expand=self._expand,
            _custom=self._custom,
        )

    def skip(self, n: int) -> "StructuredQuery":
        return StructuredQuery(
            _select=self._select,
            _filter=self._filter,
            _orderby=self._orderby,
            _top=self._top,
            _skip=n,
            _expand=self._expand,
            _custom=self._custom,
        )

    def expand(self, *nav_properties: str) -> "StructuredQuery":
        return StructuredQuery(
            _select=self._select,
            _filter=self._filter,
            _orderby=self._orderby,
            _top=self._top,
            _skip=self._skip,
            _expand=tuple(nav_properties),
            _custom=self._custom,
        )

    def custom(self, key: str, value: str) -> "StructuredQuery":
        filtered = tuple((k, v) for k, v in self._custom if k != key)
        return StructuredQuery(
            _select=self._select,
            _filter=self._filter,
            _orderby=self._orderby,
            _top=self._top,
            _skip=self._skip,
            _expand=self._expand,
            _custom=filtered + ((key, value),),
        )

    def to_params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        if self._select:
            params[QUERY_SELECT] = ",".join(self._select)
        if self._filter is not None:
            params[QUERY_FILTER] = str(self._filter)
        if self._orderby:
            params[QUERY_ORDERBY] = ",".join(f"{f} {d.value}" for f, d in self._orderby)
        if self._top is not None:
            params[QUERY_TOP] = str(self._top)
        if self._skip is not None:
            params[QUERY_SKIP] = str(self._skip)
        if self._expand:
            params[QUERY_EXPAND] = ",".join(self._expand)
        for k, v in self._custom:
            params[k] = v
        return params
