"""Unit tests for the 3 entity classes produced by consent_template.make_entities."""

from __future__ import annotations

import pytest
from odata.property import BooleanProperty

from tests.core.unit.dpi_ng.consent.unit.entities.conftest import (
    TEMPLATE_ENTITY_SPECS,
    entity_by_name,
)


def test_make_entities_returns_all_classes(template_entities):
    assert len(template_entities) == 3


@pytest.mark.parametrize("name,spec", TEMPLATE_ENTITY_SPECS.items())
def test_collection_name(template_entities, name, spec):
    cls = entity_by_name(template_entities, name)
    assert cls.__odata_collection__ == spec["collection"]


@pytest.mark.parametrize("name,spec", TEMPLATE_ENTITY_SPECS.items())
def test_pk_fields_marked(template_entities, name, spec):
    cls = entity_by_name(template_entities, name)
    for pk_field in spec["pk"]:
        prop = getattr(cls, pk_field)
        assert prop.primary_key is True


@pytest.mark.parametrize(
    "name,spec",
    [(n, s) for n, s in TEMPLATE_ENTITY_SPECS.items() if s["bool"]],
)
def test_bool_fields(template_entities, name, spec):
    cls = entity_by_name(template_entities, name)
    for field in spec["bool"]:
        assert isinstance(getattr(cls, field), BooleanProperty)


class TestTemplateThirdPartyPersDataCompositeKey:
    def test_template_id_is_pk(self, template_entities):
        cls = entity_by_name(template_entities, "TemplateThirdPartyPersData")
        assert cls.template_id.primary_key is True

    def test_third_party_id_is_pk(self, template_entities):
        cls = entity_by_name(template_entities, "TemplateThirdPartyPersData")
        assert cls.third_party_id.primary_key is True
