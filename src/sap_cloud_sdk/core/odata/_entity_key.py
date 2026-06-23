"""OData V4 entity-key path value object."""

from __future__ import annotations

from typing import Any

from sap_cloud_sdk.core.odata._request_builders import build_key_segment


class EntityKey:
    """Typed OData V4 entity-key path that supports navigation / action chaining.

    Construct with the entity-set name and key fields as keyword arguments.
    Values are serialised by :func:`~sap_cloud_sdk.core.odata.build_key_segment`:

    - ``uuid.UUID`` → unquoted (``Edm.Guid``)
    - ``str`` → single-quoted, embedded quotes doubled (``Edm.String``)
    - ``bool`` → ``true`` / ``false``

    Use the ``/`` operator to append navigation properties or bound actions,
    and :meth:`segment` to append a parameterised function suffix::

        import uuid
        from sap_cloud_sdk.core.odata import EntityKey

        key = EntityKey(
            "DocumentRelation",
            DocumentRelationID=uuid.UUID(rel_id),
            IsActiveEntity=True,
        )
        str(key)
        # "DocumentRelation(DocumentRelationID=<guid>,IsActiveEntity=true)"

        str(key / "Document")
        # "DocumentRelation(...)/Document"

        str(key / "DownloadDocument") + EntityKey.segment(DocContentVersionID="1.0")
        # "DocumentRelation(...)/DownloadDocument('1.0')"
    """

    def __init__(self, entity_set: str, **key_fields: Any) -> None:
        self._path = entity_set + build_key_segment(key_fields)

    @classmethod
    def _from_path(cls, path: str) -> "EntityKey":
        obj: EntityKey = object.__new__(cls)
        obj._path = path
        return obj

    @staticmethod
    def segment(**fields: Any) -> str:
        """Return a bare key-segment string, e.g. ``('1.0')``.

        Useful for appending parameterised function calls where the function
        name is already part of the path::

            str(key / "DownloadDocument") + EntityKey.segment(DocContentVersionID="1.0")
            # "DocumentRelation(...)/DownloadDocument('1.0')"
        """
        return build_key_segment(fields)

    def __truediv__(self, other: "str | EntityKey") -> "EntityKey":
        """Append *other* as the next path segment (``/`` operator)."""
        segment = str(other).lstrip("/")
        return EntityKey._from_path(f"{self._path}/{segment}")

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return f"EntityKey({self._path!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EntityKey):
            return self._path == other._path
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._path)
