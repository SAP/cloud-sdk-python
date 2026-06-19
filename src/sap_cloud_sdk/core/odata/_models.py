"""Protocol-level types for OData v4 entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class ODataEntity:
    """Base class for OData v4 entity types.

    Generated and hand-written entity dataclasses may inherit from this to
    allow the transport layer's generic serialiser to reflect on key fields
    and entity-set metadata without inspecting the concrete type directly.

    Subclasses declare their metadata via ClassVar annotations::

        @dataclass
        class BusinessPartner(ODataEntity):
            _entity_set: ClassVar[str] = "BusinessPartnerSet"
            _key_fields: ClassVar[list[str]] = ["BusinessPartnerID"]

            BusinessPartnerID: str = ""
            DisplayName: str = ""
    """

    _entity_set: ClassVar[str] = ""
    _key_fields: ClassVar[list[str]] = []

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict of this entity's fields."""
        result: dict[str, Any] = {}
        for f in self.__dataclass_fields__:  # type: ignore[attr-defined]
            if not f.startswith("_"):
                result[f] = getattr(self, f)
        return result

    def key_dict(self) -> dict[str, Any]:
        """Return only the key fields as a dict."""
        return {k: getattr(self, k) for k in self._key_fields}
