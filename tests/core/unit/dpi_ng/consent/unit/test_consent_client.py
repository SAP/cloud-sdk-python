"""Unit tests for ConsentClient and create_client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.core.dpi_ng.consent import (
    BearerTokenAuth,
    ClientCreationError,
    ConsentClient,
    ConsentConfig,
    create_client,
)
from sap_cloud_sdk.core.dpi_ng.consent.services import (
    ConsentConfigurationService,
    ConsentPurposeService,
    ConsentRetentionService,
    ConsentService,
    ConsentTemplateService,
)


def _entity_side_effect(svc_name: str) -> tuple:
    sizes = {
        "consentServices": 1,
        "consentPurposeExternalServices": 2,
        "consentTemplateExternalServices": 3,
        "consentRetentionExternalServices": 1,
        "consentConfigurationExternalServices": 11,
    }
    return tuple(MagicMock() for _ in range(sizes[svc_name]))


def _setup_mock(MockODataClient: MagicMock) -> MagicMock:
    mock_instance = MagicMock()
    MockODataClient.return_value = mock_instance
    mock_instance.get_entity_classes.side_effect = _entity_side_effect
    return mock_instance


@pytest.fixture
def auth() -> BearerTokenAuth:
    return BearerTokenAuth("test-token")


class TestCreateClient:
    def test_with_config(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            _setup_mock(Mock)
            config = ConsentConfig(base_url="https://example.com", auth=auth)
            client = create_client(config=config)
            assert isinstance(client, ConsentClient)

    def test_with_kwargs(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            _setup_mock(Mock)
            client = create_client(base_url="https://example.com", auth=auth)
            assert isinstance(client, ConsentClient)

    def test_missing_base_url_raises(self, auth: BearerTokenAuth) -> None:
        with pytest.raises(ClientCreationError, match="base_url"):
            create_client(auth=auth)

    def test_missing_auth_raises(self) -> None:
        with pytest.raises(ClientCreationError, match="auth"):
            create_client(base_url="https://example.com")

    def test_invalid_url_raises(self, auth: BearerTokenAuth) -> None:
        with pytest.raises(ClientCreationError):
            create_client(base_url="not-a-url", auth=auth)

    def test_missing_both_raises(self) -> None:
        with pytest.raises(ClientCreationError, match="base_url"):
            create_client()

    def test_returns_consent_client_instance(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            _setup_mock(Mock)
            config = ConsentConfig(base_url="https://example.com", auth=auth)
            result = create_client(config=config)
            assert type(result).__name__ == "ConsentClient"


class TestConsentClientAttributes:
    def test_service_types(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            _setup_mock(Mock)
            config = ConsentConfig(base_url="https://example.com", auth=auth)
            client = ConsentClient(config)
            assert isinstance(client.consents, ConsentService)
            assert isinstance(client.purposes, ConsentPurposeService)
            assert isinstance(client.templates, ConsentTemplateService)
            assert isinstance(client.retention, ConsentRetentionService)
            assert isinstance(client.configuration, ConsentConfigurationService)

    def test_odata_client_instantiated(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            _setup_mock(Mock)
            config = ConsentConfig(base_url="https://example.com", auth=auth)
            ConsentClient(config)
            Mock.assert_called_once_with(config)

    def test_all_five_services_present(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            _setup_mock(Mock)
            config = ConsentConfig(base_url="https://example.com", auth=auth)
            client = ConsentClient(config)
            for attr in (
                "consents",
                "purposes",
                "templates",
                "retention",
                "configuration",
            ):
                assert hasattr(client, attr)


class TestConsentClientLifecycle:
    def test_context_manager_closes(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            mock_instance = MagicMock()
            Mock.return_value = mock_instance
            mock_instance.get_entity_classes.side_effect = _entity_side_effect
            config = ConsentConfig(base_url="https://example.com", auth=auth)
            with ConsentClient(config):
                pass
            mock_instance.close.assert_called_once()

    def test_close_delegates_to_odata(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            mock_instance = MagicMock()
            Mock.return_value = mock_instance
            mock_instance.get_entity_classes.side_effect = _entity_side_effect
            config = ConsentConfig(base_url="https://example.com", auth=auth)
            client = ConsentClient(config)
            client.close()
            mock_instance.close.assert_called_once()

    def test_context_manager_returns_client(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            mock_instance = MagicMock()
            Mock.return_value = mock_instance
            mock_instance.get_entity_classes.side_effect = _entity_side_effect
            config = ConsentConfig(base_url="https://example.com", auth=auth)
            with ConsentClient(config) as client:
                assert isinstance(client, ConsentClient)

    def test_close_called_even_on_exception(self, auth: BearerTokenAuth) -> None:
        with patch(
            "sap_cloud_sdk.core.dpi_ng.consent.client._ConsentODataClient"
        ) as Mock:
            mock_instance = MagicMock()
            Mock.return_value = mock_instance
            mock_instance.get_entity_classes.side_effect = _entity_side_effect
            config = ConsentConfig(base_url="https://example.com", auth=auth)
            try:
                with ConsentClient(config):
                    raise RuntimeError("boom")
            except RuntimeError:
                pass
            mock_instance.close.assert_called_once()
