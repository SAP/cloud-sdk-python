"""OData v4 response parsing and entity deserialisation."""

from __future__ import annotations

import dataclasses
from typing import Any, TypeVar

from sap_cloud_sdk.core.odata.exceptions import ODataDeserializationError

T = TypeVar("T")


def deserialize_single(data: dict[str, Any], entity_type: type[T]) -> T:
    """Deserialise a single OData entity dict into *entity_type*.

    Accepts both a raw entity dict and an OData response envelope
    (``{"value": {...}}``).  Unknown fields in *data* are silently ignored so
    that server-side ``@odata.*`` annotations do not break deserialisation.
    """
    if not dataclasses.is_dataclass(entity_type):
        raise ODataDeserializationError(
            f"{entity_type!r} is not a dataclass — cannot deserialize"
        )
    try:
        payload = data.get("value", data) if isinstance(data.get("value"), dict) else data
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
        items: list[dict[str, Any]] = data.get("value", [])
        return [deserialize_single(item, entity_type) for item in items]
    except ODataDeserializationError:
        raise
    except Exception as exc:
        raise ODataDeserializationError(
            f"Failed to deserialize collection of {entity_type.__name__}: {exc}"
        ) from exc


def next_link(data: dict[str, Any]) -> str | None:
    """Extract ``@odata.nextLink`` from a collection response, or ``None``."""
    return data.get("@odata.nextLink")
