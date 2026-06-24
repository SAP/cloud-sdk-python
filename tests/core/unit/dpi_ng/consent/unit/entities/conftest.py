"""Shared fixtures and entity specs for all entity unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from odata.entity import declarative_base

CONSENT_ENTITY_SPECS = {
    "Consent": {
        "collection": "consents",
        "pk": ["consent_id"],
        "bool": ["purpose_sensitive_data_flag", "third_party_sensitive_data_flag"],
        "int": [],
    },
}

CONFIGURATION_ENTITY_SPECS = {
    "ThirdParty": {
        "collection": "thirdParties",
        "pk": ["third_party_id"],
        "bool": [],
        "int": [],
    },
    "Jurisdiction": {
        "collection": "jurisdictions",
        "pk": ["jurisdiction_id"],
        "bool": [],
        "int": [],
    },
    "JurisdictionText": {
        "collection": "jurisdictionTexts",
        "pk": ["jurisdiction_id", "language_code"],
        "bool": [],
        "int": [],
    },
    "Language": {
        "collection": "languages",
        "pk": ["language_code"],
        "bool": [],
        "int": [],
    },
    "LanguageDescription": {
        "collection": "languageDescriptions",
        "pk": ["language_code"],
        "bool": [],
        "int": [],
    },
    "SourceInfo": {
        "collection": "sourceInfos",
        "pk": ["source_id"],
        "bool": [],
        "int": [],
    },
    "Controller": {
        "collection": "controllers",
        "pk": ["controller_id"],
        "bool": [],
        "int": [],
    },
    "DataSubjectType": {
        "collection": "dataSubjectTypes",
        "pk": ["data_subject_type_id"],
        "bool": [],
        "int": [],
    },
    "Application": {
        "collection": "applications",
        "pk": ["application_id"],
        "bool": [],
        "int": [],
    },
    "MasterDataSource": {
        "collection": "masterDataSources",
        "pk": ["master_data_source_id"],
        "bool": [],
        "int": [],
    },
    "OutboundChannelType": {
        "collection": "outboundChannelTypes",
        "pk": ["outbound_channel_type_id"],
        "bool": [],
        "int": [],
    },
}

PURPOSE_ENTITY_SPECS = {
    "ConsentPurpose": {
        "collection": "consentPurposes",
        "pk": ["purpose_id"],
        "bool": ["sensitive_data_flag"],
        "int": [],
    },
    "ConsentPurposeText": {
        "collection": "consentPurposeTexts",
        "pk": ["purpose_id", "type_code", "language_code"],
        "bool": [],
        "int": [],
    },
}

RETENTION_ENTITY_SPECS = {
    "ConsentRetentionRule": {
        "collection": "consentRetentionRules",
        "pk": ["rule_id"],
        "bool": [],
        "int": ["retention_years", "retention_months", "retention_days"],
    },
}

TEMPLATE_ENTITY_SPECS = {
    "ConsentTemplate": {
        "collection": "consentTemplates",
        "pk": ["template_id"],
        "bool": [],
        "int": [],
    },
    "ConsentTemplateText": {
        "collection": "consentTemplateTexts",
        "pk": ["template_id", "type_code", "language_code"],
        "bool": [],
        "int": [],
    },
    "TemplateThirdPartyPersData": {
        "collection": "templateThirdPartyPersDatas",
        "pk": ["template_id", "third_party_id"],
        "bool": ["sensitive_data_flag"],
        "int": [],
    },
}


def _make_service():
    svc = MagicMock()
    svc.Entity = declarative_base()
    return svc


def entity_by_name(entities_tuple, name):
    return next(c for c in entities_tuple if c.__name__ == name)


@pytest.fixture(scope="module")
def consent_entities():
    from sap_cloud_sdk.core.dpi_ng.consent.entities.consent import _make_entities as make_entities
    return make_entities(_make_service())


@pytest.fixture(scope="module")
def config_entities():
    from sap_cloud_sdk.core.dpi_ng.consent.entities.consent_configuration import _make_entities as make_entities
    return make_entities(_make_service())


@pytest.fixture(scope="module")
def purpose_entities():
    from sap_cloud_sdk.core.dpi_ng.consent.entities.consent_purpose import _make_entities as make_entities
    return make_entities(_make_service())


@pytest.fixture(scope="module")
def retention_entities():
    from sap_cloud_sdk.core.dpi_ng.consent.entities.consent_retention import _make_entities as make_entities
    return make_entities(_make_service())


@pytest.fixture(scope="module")
def template_entities():
    from sap_cloud_sdk.core.dpi_ng.consent.entities.consent_template import _make_entities as make_entities
    return make_entities(_make_service())
