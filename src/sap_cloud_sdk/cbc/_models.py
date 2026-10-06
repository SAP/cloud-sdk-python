"""Data models for the CBC (Central Business Configuration) module.

All models use Pydantic v2 with ``frozen=True`` and camelCase alias support
so they map directly to the CBC REST API JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from pydantic import BaseModel, ConfigDict, Field


class _FrozenModel(BaseModel):
    """Base model: immutable, accepts both snake_case and camelCase field names."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)


# ---------------------------------------------------------------------------
# Consumption version models
# ---------------------------------------------------------------------------


class NNV(_FrozenModel):
    """Namespace-Name-Version tuple identifying a reference content version."""

    namespace: str
    name: str
    version: str

    def __str__(self) -> str:
        return f"{self.namespace}.{self.name}.{self.version}"


class ConsumptionVersion(_FrozenModel):
    """A snapshot of the business configuration for an app tenant at a point in time.

    Attributes:
        version: Version identifier.
        created_date: Creation timestamp.
        modified_date: Last modification timestamp.
        ref_content: Reference content NNV this version is based on, if applicable.
    """

    version: str
    created_date: datetime | None = Field(default=None, alias="createdDate")
    modified_date: datetime | None = Field(default=None, alias="modifiedDate")
    ref_content: NNV | None = Field(default=None, alias="referenceContentDetails")


class ConsumptionVersions(_FrozenModel):
    """Collection of consumption versions returned by the CBC API.

    Attributes:
        items: List of :class:`ConsumptionVersion` objects.
    """

    items: list[ConsumptionVersion]

    def latest(self) -> ConsumptionVersion | None:
        """Return the latest version.

        Prefers most-recent ``modifiedDate``; falls back to ``createdDate``; falls
        back to last item in the list.

        Returns:
            Latest :class:`ConsumptionVersion`, or ``None`` if the list is empty.
        """
        if not self.items:
            return None
        dated = [v for v in self.items if v.modified_date is not None]
        if dated:
            return max(dated, key=lambda v: cast(datetime, v.modified_date))
        created = [v for v in self.items if v.created_date is not None]
        if created:
            return max(created, key=lambda v: cast(datetime, v.created_date))
        return self.items[-1]


# ---------------------------------------------------------------------------
# Entity models
# ---------------------------------------------------------------------------


class ConfigObjectEntity(_FrozenModel):
    """One entity listed under a config object by the ``configurationObjects`` API.

    Attributes:
        entity_id: Authored entity key (e.g. ``"payment-mode"``), used directly
            in the entity-data URL path.
    """

    entity_id: str = Field(alias="entityId")


class ConfigObjectEntry(_FrozenModel):
    """One config object and its entities as returned by the API.

    Attributes:
        config_object_id: Authored config object identifier (e.g. ``"payment-config"``).
        entities: Entities belonging to this config object.
    """

    config_object_id: str = Field(alias="configurationObjectId")
    entities: list[ConfigObjectEntity]


class ConfigObjectList(_FrozenModel):
    """Config objects for a consumption version, already grouped by the API.

    Attributes:
        items: List of :class:`ConfigObjectEntry` objects.
    """

    items: list[ConfigObjectEntry]


class EntityData:
    """Configuration data for an entity.

    Wraps the raw API response data and enforces shape at access time.
    """

    def __init__(self, raw: list[dict[str, Any]] | dict[str, Any]) -> None:
        self._raw = raw

    def is_list(self) -> bool:
        """Return ``True`` if the data is a list (``as_list()`` is safe to call)."""
        return isinstance(self._raw, list)

    def is_object(self) -> bool:
        """Return ``True`` if the data is a dict (``as_object()`` is safe to call)."""
        return isinstance(self._raw, dict)

    def value(self) -> list[dict[str, Any]] | dict[str, Any]:
        """Return the data as-is, without asserting its shape.

        Use :meth:`as_list` / :meth:`as_object` when you expect a specific shape,
        or :meth:`is_list` / :meth:`is_object` to check first.
        """
        return self._raw

    def as_list(self) -> list[dict[str, Any]]:
        """Return the data as a list of objects.

        Raises:
            ValueError: If the data is a dict, not a list.
        """
        if not isinstance(self._raw, list):
            raise ValueError(
                "Entity data is a dict, not a list — use as_object() instead."
            )
        return self._raw

    def as_object(self) -> dict[str, Any]:
        """Return the data as a dict.

        Raises:
            ValueError: If the data is a list, not a dict.
        """
        if not isinstance(self._raw, dict):
            raise ValueError(
                "Entity data is a list, not a dict — use as_list() instead."
            )
        return self._raw

    def __repr__(self) -> str:
        return f"EntityData({self._raw!r})"


@dataclass
class ConfigEntity:
    """A single entity within a config object.

    Attributes:
        entity_id: Authored entity identifier (e.g. ``"payment-mode"``).
        data: Configuration data for this entity.
    """

    entity_id: str
    data: EntityData


@dataclass
class ConfigObject:
    """A configuration object and its entities.

    Attributes:
        config_object_id: Authored config object identifier (e.g. ``"payment-config"``).
        entities: Entity data for all entities in this config object.
    """

    config_object_id: str
    entities: list[ConfigEntity]

    def get_config_entity(self, entity_id: str) -> ConfigEntity | None:
        """Return the entity with the given entity ID.

        Args:
            entity_id: Authored entity identifier.

        Returns:
            Matching :class:`ConfigEntity`, or ``None`` if not found.
        """
        return next((e for e in self.entities if e.entity_id == entity_id), None)


@dataclass
class ConfigData:
    """Complete business configuration — all config objects for one consumption version.

    Attributes:
        consumption_version: Version this data was fetched from.
        app_tenant_id: Application tenant this data belongs to.
        config_objects: Configuration objects and their entity data.
    """

    consumption_version: str
    app_tenant_id: str
    config_objects: list[ConfigObject]

    def get_config_object(self, config_object_id: str) -> ConfigObject | None:
        """Return the config object with the given ID.

        Args:
            config_object_id: Authored config object identifier.

        Returns:
            Matching :class:`ConfigObject`, or ``None`` if not found.
        """
        return next(
            (
                co
                for co in self.config_objects
                if co.config_object_id == config_object_id
            ),
            None,
        )

    def get_config_entity(
        self, config_object_id: str, entity_id: str
    ) -> ConfigEntity | None:
        """Return the entity for the given config object and entity IDs.

        Args:
            config_object_id: Authored config object identifier.
            entity_id: Authored entity identifier.

        Returns:
            Matching :class:`ConfigEntity`, or ``None`` if not found.
        """
        co = self.get_config_object(config_object_id)
        return co.get_config_entity(entity_id) if co is not None else None


# ---------------------------------------------------------------------------
# API error model
# ---------------------------------------------------------------------------


class ApiError(_FrozenModel):
    """Error payload returned by the CBC API.

    Attributes:
        code: Application-level error code.
        message: Human-readable error message.
    """

    code: str
    message: str

    @classmethod
    def from_response(cls, response_body: bytes | None) -> "ApiError":
        """Parse a CBC API error response body.

        Falls back to a generic ``UNKNOWN_ERROR`` when the body is absent or
        unparseable.

        Args:
            response_body: Raw HTTP response body.

        Returns:
            Parsed :class:`ApiError`.
        """
        if not response_body:
            return cls(code="UNKNOWN_ERROR", message="No response body")
        try:
            data = json.loads(response_body.decode("utf-8"))
            if isinstance(data, dict) and "error" in data:
                return cls(
                    code=data["error"].get("code", "UNKNOWN_ERROR"),
                    message=data["error"].get("message", "Unknown error"),
                )
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return cls(
            code="UNKNOWN_ERROR",
            message=response_body.decode("utf-8", errors="replace").strip(),
        )
