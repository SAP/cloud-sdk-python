"""Unit tests for the 11 entity classes produced by consent_configuration.make_entities."""

from __future__ import annotations

import pytest
from odata.property import BooleanProperty

from tests.core.unit.dpi_ng.consent.unit.entities.conftest import CONFIGURATION_ENTITY_SPECS, entity_by_name


def test_make_entities_returns_all_classes(config_entities):
    assert len(config_entities) == 11


@pytest.mark.parametrize("name,spec", CONFIGURATION_ENTITY_SPECS.items())
def test_collection_name(config_entities, name, spec):
    cls = entity_by_name(config_entities, name)
    assert cls.__odata_collection__ == spec["collection"]


@pytest.mark.parametrize("name,spec", CONFIGURATION_ENTITY_SPECS.items())
def test_pk_fields_marked(config_entities, name, spec):
    cls = entity_by_name(config_entities, name)
    for pk_field in spec["pk"]:
        prop = getattr(cls, pk_field)
        assert prop.primary_key is True


@pytest.mark.parametrize(
    "name,spec",
    [(n, s) for n, s in CONFIGURATION_ENTITY_SPECS.items() if s["bool"]],
)
def test_bool_fields(config_entities, name, spec):
    cls = entity_by_name(config_entities, name)
    for field in spec["bool"]:
        assert isinstance(getattr(cls, field), BooleanProperty)
