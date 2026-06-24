"""Unit tests for ConsentConfigurationService."""

from __future__ import annotations

import pytest


CRUD_ENTITIES = [
    (
        "ThirdParty",
        "third_party_id",
        "list_third_parties",
        "get_third_party",
        "create_third_party",
        "update_third_party",
        "delete_third_party",
    ),
    (
        "Jurisdiction",
        "jurisdiction_id",
        "list_jurisdictions",
        "get_jurisdiction",
        "create_jurisdiction",
        "update_jurisdiction",
        "delete_jurisdiction",
    ),
    (
        "SourceInfo",
        "source_id",
        "list_source_infos",
        "get_source_info",
        "create_source_info",
        "update_source_info",
        "delete_source_info",
    ),
    (
        "Controller",
        "controller_id",
        "list_controllers",
        "get_controller",
        "create_controller",
        "update_controller",
        "delete_controller",
    ),
    (
        "DataSubjectType",
        "data_subject_type_id",
        "list_data_subject_types",
        "get_data_subject_type",
        "create_data_subject_type",
        "update_data_subject_type",
        "delete_data_subject_type",
    ),
    (
        "Application",
        "application_id",
        "list_applications",
        "get_application",
        "create_application",
        "update_application",
        "delete_application",
    ),
    (
        "MasterDataSource",
        "master_data_source_id",
        "list_master_data_sources",
        "get_master_data_source",
        "create_master_data_source",
        "update_master_data_source",
        "delete_master_data_source",
    ),
    (
        "OutboundChannelType",
        "outbound_channel_type_id",
        "list_outbound_channel_types",
        "get_outbound_channel_type",
        "create_outbound_channel_type",
        "update_outbound_channel_type",
        "delete_outbound_channel_type",
    ),
]

_PARAM_IDS = [row[0] for row in CRUD_ENTITIES]


@pytest.fixture
def svc(mock_config_client):
    from sap_cloud_sdk.core.dpi_ng.consent.services.consent_configuration_service import (
        ConsentConfigurationService,
    )

    return ConsentConfigurationService(mock_config_client)


# ---------------------------------------------------------------------------
# Parametrized CRUD — Strategy A
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("row", CRUD_ENTITIES, ids=_PARAM_IDS)
def test_list_calls_query(svc, row):
    getattr(svc, row[2])()
    svc._client.query.assert_called()


@pytest.mark.parametrize("row", CRUD_ENTITIES, ids=_PARAM_IDS)
def test_get_calls_query_get(svc, row):
    getattr(svc, row[3])("some-id")
    svc._client.query.return_value.get.assert_called_with("some-id")


@pytest.mark.parametrize("row", CRUD_ENTITIES, ids=_PARAM_IDS)
def test_create_calls_save(svc, row):
    getattr(svc, row[4])({"name": "x"})
    svc._client.save.assert_called_once()


@pytest.mark.parametrize("row", CRUD_ENTITIES, ids=_PARAM_IDS)
def test_update_calls_save(svc, row):
    getattr(svc, row[5])("some-id", {"name": "y"})
    svc._client.save.assert_called_once()


@pytest.mark.parametrize("row", CRUD_ENTITIES, ids=_PARAM_IDS)
def test_delete_calls_delete_entity(svc, row):
    getattr(svc, row[6])("some-id")
    svc._client.delete_entity.assert_called_once()


# ---------------------------------------------------------------------------
# Query helper — _apply_query
# ---------------------------------------------------------------------------


def test_list_with_filter_kwarg(svc):
    svc.list_third_parties(filter="third_party_name eq 'ACME'")
    svc._client.query.return_value.raw.assert_called_with(
        {"$filter": "third_party_name eq 'ACME'"}
    )


def test_list_with_top_kwarg(svc):
    svc.list_third_parties(top=10)
    svc._client.query.return_value.limit.assert_called_with(10)


def test_list_with_skip_kwarg(svc):
    svc.list_third_parties(skip=5)
    svc._client.query.return_value.offset.assert_called_with(5)


def test_list_with_orderby_kwarg(svc):
    svc.list_third_parties(orderby="third_party_name asc")
    svc._client.query.return_value.raw.assert_called_with(
        {"$orderby": "third_party_name asc"}
    )


# ---------------------------------------------------------------------------
# JurisdictionText — composite key
# ---------------------------------------------------------------------------


class TestJurisdictionText:
    def test_list(self, svc):
        svc.list_jurisdiction_texts()
        svc._client.query.assert_called()

    def test_create(self, svc):
        svc.create_jurisdiction_text({"description": "x"})
        svc._client.save.assert_called_once()

    def test_update_composite_key(self, svc):
        svc.update_jurisdiction_text("jur-1", "EN", {"description": "y"})
        svc._client.query.return_value.get.assert_called_with(
            jurisdictionId="jur-1", languageCode="EN"
        )

    def test_update_calls_save(self, svc):
        svc.update_jurisdiction_text("jur-1", "EN", {"description": "y"})
        svc._client.save.assert_called_once()

    def test_delete_composite_key(self, svc):
        svc.delete_jurisdiction_text("jur-1", "EN")
        svc._client.query.return_value.get.assert_called_with(
            jurisdictionId="jur-1", languageCode="EN"
        )

    def test_delete_calls_delete_entity(self, svc):
        svc.delete_jurisdiction_text("jur-1", "EN")
        svc._client.delete_entity.assert_called_once()


# ---------------------------------------------------------------------------
# Language — no create method
# ---------------------------------------------------------------------------


class TestLanguage:
    def test_list(self, svc):
        svc.list_languages()
        svc._client.query.assert_called()

    def test_get(self, svc):
        svc.get_language("EN")
        svc._client.query.return_value.get.assert_called_with("EN")


# ---------------------------------------------------------------------------
# LanguageDescription
# ---------------------------------------------------------------------------


class TestLanguageDescription:
    def test_list(self, svc):
        svc.list_language_descriptions()
        svc._client.query.assert_called()

    def test_create(self, svc):
        svc.create_language_description({"description": "x"})
        svc._client.save.assert_called_once()

    def test_update(self, svc):
        svc.update_language_description("EN", {"description": "English"})
        svc._client.save.assert_called_once()

    def test_update_fetches_by_code(self, svc):
        svc.update_language_description("FR", {"description": "French"})
        svc._client.query.return_value.get.assert_called_with("FR")

    def test_delete(self, svc):
        svc.delete_language_description("EN")
        svc._client.delete_entity.assert_called_once()

    def test_delete_fetches_by_code(self, svc):
        svc.delete_language_description("ES")
        svc._client.query.return_value.get.assert_called_with("ES")


