"""Unit tests for the entity class produced by consent._make_entities."""

from __future__ import annotations

import pytest
from odata.property import BooleanProperty, StringProperty, UUIDProperty

from tests.core.unit.dpi_ng.consent.unit.entities.conftest import (
    CONSENT_ENTITY_SPECS,
    entity_by_name,
)


def test_make_entities_returns_all_classes(consent_entities):
    assert len(consent_entities) == 1


@pytest.mark.parametrize("name,spec", CONSENT_ENTITY_SPECS.items())
def test_collection_name(consent_entities, name, spec):
    cls = entity_by_name(consent_entities, name)
    assert cls.__odata_collection__ == spec["collection"]


@pytest.mark.parametrize("name,spec", CONSENT_ENTITY_SPECS.items())
def test_pk_fields_marked(consent_entities, name, spec):
    cls = entity_by_name(consent_entities, name)
    for pk_field in spec["pk"]:
        prop = getattr(cls, pk_field)
        assert prop.primary_key is True


@pytest.mark.parametrize(
    "name,spec",
    [(n, s) for n, s in CONSENT_ENTITY_SPECS.items() if s["bool"]],
)
def test_bool_fields(consent_entities, name, spec):
    cls = entity_by_name(consent_entities, name)
    for field in spec["bool"]:
        assert isinstance(getattr(cls, field), BooleanProperty)


class TestConsentEntity:
    def test_consent_id_is_uuid_pk(self, consent_entities):
        cls = entity_by_name(consent_entities, "Consent")
        assert isinstance(cls.consent_id, UUIDProperty)
        assert cls.consent_id.primary_key is True

    def test_consent_has_single_pk(self, consent_entities):
        cls = entity_by_name(consent_entities, "Consent")
        pk_props = [
            name
            for name, val in vars(cls).items()
            if isinstance(val, UUIDProperty) and getattr(val, "primary_key", False)
        ]
        assert pk_props == ["consent_id"]

    def test_consent_purpose_sensitive_data_flag_is_boolean(self, consent_entities):
        cls = entity_by_name(consent_entities, "Consent")
        assert isinstance(cls.purpose_sensitive_data_flag, BooleanProperty)

    def test_consent_third_party_sensitive_data_flag_is_boolean(self, consent_entities):
        cls = entity_by_name(consent_entities, "Consent")
        assert isinstance(cls.third_party_sensitive_data_flag, BooleanProperty)

    def test_consent_tenant_is_string(self, consent_entities):
        cls = entity_by_name(consent_entities, "Consent")
        assert isinstance(cls.tenant, StringProperty)
