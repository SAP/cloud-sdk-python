"""Unit tests for the 1 entity class produced by consent_retention.make_entities."""

from __future__ import annotations

import pytest
from odata.property import IntegerProperty

from tests.core.unit.dpi_ng.consent.unit.entities.conftest import (
    RETENTION_ENTITY_SPECS,
    entity_by_name,
)


def test_make_entities_returns_all_classes(retention_entities):
    assert len(retention_entities) == 1


@pytest.mark.parametrize("name,spec", RETENTION_ENTITY_SPECS.items())
def test_collection_name(retention_entities, name, spec):
    cls = entity_by_name(retention_entities, name)
    assert cls.__odata_collection__ == spec["collection"]


@pytest.mark.parametrize("name,spec", RETENTION_ENTITY_SPECS.items())
def test_pk_fields_marked(retention_entities, name, spec):
    cls = entity_by_name(retention_entities, name)
    for pk_field in spec["pk"]:
        prop = getattr(cls, pk_field)
        assert prop.primary_key is True


@pytest.mark.parametrize(
    "name,spec",
    [(n, s) for n, s in RETENTION_ENTITY_SPECS.items() if s["int"]],
)
def test_integer_fields(retention_entities, name, spec):
    cls = entity_by_name(retention_entities, name)
    for field in spec["int"]:
        assert isinstance(getattr(cls, field), IntegerProperty)
