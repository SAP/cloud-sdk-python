"""Filter expression DSL for OData v4 $filter query options."""

from __future__ import annotations

import uuid
from typing import Any


def quote_odata_string_key(value: str) -> str:
    """Quote and escape a string value for use in an OData V4 entity key segment.

    OData V4 §5.1.1.6.2 requires single-quoted string literals with embedded
    single quotes doubled.

    Example::

        path = f"Documents(DocID={quote_odata_string_key(doc_id)})"
    """
    return "'" + value.replace("'", "''") + "'"


def quote_odata_guid_key(value: str) -> str:
    """Validate and serialise an ``Edm.Guid`` value for an OData V4 key segment.

    OData V4 §5.1.1.6.2 represents ``Edm.Guid`` keys *without* single quotes.
    Injection protection comes from UUID validation rather than escaping.

    Raises:
        ValueError: If *value* is not a well-formed UUID.
    """
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"invalid OData Edm.Guid key: {value!r}") from exc


def _format_value(value: Any) -> str:
    """Serialise a Python value to an OData v4 literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


class FilterExpression:
    """Composable OData v4 ``$filter`` expression.

    Build expressions via :meth:`field` and combine them with :meth:`and_`,
    :meth:`or_`, and :meth:`not_`::

        f = (
            FilterExpression.field("Price").gt(100)
            .and_(FilterExpression.field("Category").eq("Books"))
        )
        str(f)  # "(Price gt 100) and (Category eq 'Books')"
    """

    __slots__ = ("_expr",)

    def __init__(self, expr: str) -> None:
        self._expr = expr

    @staticmethod
    def field(name: str) -> "_FieldRef":
        """Start a comparison expression for *name*."""
        return _FieldRef(name)

    def and_(self, other: "FilterExpression") -> "FilterExpression":
        return FilterExpression(f"({self._expr}) and ({other._expr})")

    def or_(self, other: "FilterExpression") -> "FilterExpression":
        return FilterExpression(f"({self._expr}) or ({other._expr})")

    def not_(self) -> "FilterExpression":
        return FilterExpression(f"not ({self._expr})")

    def __str__(self) -> str:
        return self._expr

    def __repr__(self) -> str:
        return f"FilterExpression({self._expr!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FilterExpression):
            return self._expr == other._expr
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._expr)


class _FieldRef:
    """Intermediate object: a field name awaiting a comparison operator."""

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def eq(self, value: Any) -> FilterExpression:
        return FilterExpression(f"{self._name} eq {_format_value(value)}")

    def ne(self, value: Any) -> FilterExpression:
        return FilterExpression(f"{self._name} ne {_format_value(value)}")

    def lt(self, value: Any) -> FilterExpression:
        return FilterExpression(f"{self._name} lt {_format_value(value)}")

    def le(self, value: Any) -> FilterExpression:
        return FilterExpression(f"{self._name} le {_format_value(value)}")

    def gt(self, value: Any) -> FilterExpression:
        return FilterExpression(f"{self._name} gt {_format_value(value)}")

    def ge(self, value: Any) -> FilterExpression:
        return FilterExpression(f"{self._name} ge {_format_value(value)}")

    def contains(self, value: str) -> FilterExpression:
        return FilterExpression(f"contains({self._name}, {_format_value(value)})")

    def starts_with(self, value: str) -> FilterExpression:
        return FilterExpression(f"startswith({self._name}, {_format_value(value)})")

    def ends_with(self, value: str) -> FilterExpression:
        return FilterExpression(f"endswith({self._name}, {_format_value(value)})")
