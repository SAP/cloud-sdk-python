"""Shared fixtures for service-layer unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sap_cloud_sdk.core.dpi_ng.consent.client import _ODataClient


def _make_mock_client(entities_module):
    svc = MagicMock()
    c = MagicMock(spec=_ODataClient)
    c.get_entity_classes.return_value = entities_module._make_entities(svc)
    q = MagicMock()
    q.all.return_value = []
    q.get.return_value = MagicMock()
    q.raw.return_value = q
    q.limit.return_value = q
    q.offset.return_value = q
    c.query.return_value = q
    return c


@pytest.fixture
def mock_consent_client():
    from sap_cloud_sdk.core.dpi_ng.consent.entities import consent as m
    return _make_mock_client(m)


@pytest.fixture
def mock_config_client():
    from sap_cloud_sdk.core.dpi_ng.consent.entities import consent_configuration as m
    return _make_mock_client(m)


@pytest.fixture
def mock_purpose_client():
    from sap_cloud_sdk.core.dpi_ng.consent.entities import consent_purpose as m
    return _make_mock_client(m)


@pytest.fixture
def mock_retention_client():
    from sap_cloud_sdk.core.dpi_ng.consent.entities import consent_retention as m
    return _make_mock_client(m)


@pytest.fixture
def mock_template_client():
    from sap_cloud_sdk.core.dpi_ng.consent.entities import consent_template as m
    return _make_mock_client(m)
