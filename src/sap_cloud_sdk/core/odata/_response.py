"""OData v4 response parsing and entity deserialisation."""

from __future__ import annotations

import dataclasses
from typing import Any, TypeVar

from sap_cloud_sdk.core.odata._constants import RESPONSE_NEXT_LINK, RESPONSE_VALUE
from sap_cloud_sdk.core.odata.exceptions import ODataDeserializationError

T = TypeVar("T")


def deserialize_single(data: dict[str, Any], entity_type: type[T]) -> T:
    """Deserialise a single OData entity dict into *entity_type*.

    If *entity_type* defines a ``from_dict`` classmethod, it is called with
    the raw payload dict — this supports entity types that use custom field
    mapping (e.g. PascalCase OData names → snake_case Python attributes).

    Otherwise the generic reflection path is used: *entity_type* must be a
    dataclass whose field names match the OData property names exactly.

    Accepts both a raw entity dict and an OData response envelope
    (``{"value": {...}}``).  Unknown fields in *data* are silently ignored so
    that server-side ``@odata.*`` annotations do not break deserialisation.
    """
    if callable(getattr(entity_type, "from_dict", None)):
        payload = (
            data.get(RESPONSE_VALUE, data)
            if isinstance(data.get(RESPONSE_VALUE), dict)
            else data
        )
        return entity_type.from_dict(payload)  # type: ignore[union-attr]  # ty: ignore[unresolved-attribute]

    if not dataclasses.is_dataclass(entity_type):
        raise ODataDeserializationError(
            f"{entity_type!r} is not a dataclass — cannot deserialize"
        )
    try:
        payload = (
            data.get(RESPONSE_VALUE, data)
            if isinstance(data.get(RESPONSE_VALUE), dict)
            else data
        )
        known = {f.name for f in dataclasses.fields(entity_type)}  # type: ignore[arg-type]
        kwargs = {k: v for k, v in payload.items() if k in known}
        return entity_type(**kwargs)  # type: ignore[call-arg]
    except Exception as exc:
        raise ODataDeserializationError(
            f"Failed to deserialize {entity_type.__name__}: {exc}"
        ) from exc


def deserialize_collection(data: dict[str, Any], entity_type: type[T]) -> list[T]:
    """Deserialise an OData collection response into a list of *entity_type*.

    Expects ``{"value": [...]}`` envelope.  Returns an empty list when the
    ``value`` key is absent.
    """
    if not dataclasses.is_dataclass(entity_type):
        raise ODataDeserializationError(
            f"{entity_type!r} is not a dataclass — cannot deserialize"
        )
    try:
        items: list[dict[str, Any]] = data.get(RESPONSE_VALUE, [])
        return [deserialize_single(item, entity_type) for item in items]
    except ODataDeserializationError:
        raise
    except Exception as exc:
        raise ODataDeserializationError(
            f"Failed to deserialize collection of {entity_type.__name__}: {exc}"
        ) from exc


def next_link(data: dict[str, Any]) -> str | None:
    """Extract ``@odata.nextLink`` from a collection response, or ``None``."""
    return data.get(RESPONSE_NEXT_LINK)
