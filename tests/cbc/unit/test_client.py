"""Unit tests for DefaultClient and create_client."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import httpx
import json
import pytest

from sap_cloud_sdk.cbc.client import DefaultClient, create_client
from sap_cloud_sdk.cbc.exceptions import (
    CBCClientError,
    CBCNetworkError,
    CBCServerError,
)
from sap_cloud_sdk.cbc._models import ConfigData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _app_tid(value: str = "app-tenant") -> Callable[[], str]:
    return lambda: value


def _mock_response(
    status_code: int = 200,
    json_body: Any = None,
    content: bytes | None = None,
) -> httpx.Response:
    if content is not None:
        return httpx.Response(status_code=status_code, content=content)
    body = json.dumps(json_body or {}).encode()
    return httpx.Response(
        status_code=status_code,
        content=body,
        headers={"content-type": "application/json"},
    )


def _make_client(
    base_url: str = "https://cbc.example.ondemand.com",
    app_tenant_id: Callable[[], str] | None = None,
) -> tuple[DefaultClient, MagicMock]:
    mock_http = MagicMock(spec=httpx.Client)
    client = DefaultClient(
        base_url=lambda: base_url,
        app_tenant_id=app_tenant_id or _app_tid(),
        http_client=mock_http,
    )
    return client, mock_http


# ---------------------------------------------------------------------------
# DefaultClient — app_tenant_id callable
# ---------------------------------------------------------------------------


class TestAppTenantIdCallable:
    def test_callable_is_invoked_on_each_call(self):
        call_count = 0

        def app_tenant_id_fn() -> str:
            nonlocal call_count
            call_count += 1
            return "app-tenant"

        mock_http = MagicMock(spec=httpx.Client)
        mock_http.request.return_value = _mock_response(
            json_body={"items": [{"version": "cv1"}]}
        )
        client = DefaultClient(
            base_url=lambda: "https://cbc.example.ondemand.com",
            app_tenant_id=app_tenant_id_fn,
            http_client=mock_http,
        )
        client.get_consumption_versions()
        client.get_consumption_versions()
        assert call_count == 2


# ---------------------------------------------------------------------------
# DefaultClient — URL building
# ---------------------------------------------------------------------------


class TestConfigurationsUrl:
    def test_joins_base_url_and_path_verbatim(self):
        client, _ = _make_client("https://my-tenant.cbc.example.ondemand.com")
        url = client._configurations_url(
            "https://my-tenant.cbc.example.ondemand.com", "/consumptionVersions"
        )
        assert url == (
            "https://my-tenant.cbc.example.ondemand.com"
            "/configuration/v1/consumptionVersions"
        )


# ---------------------------------------------------------------------------
# DefaultClient — get_consumption_versions
# ---------------------------------------------------------------------------


class TestGetConsumptionVersions:
    def test_returns_parsed_versions(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={"items": [{"version": "cv1"}]}
        )
        result = client.get_consumption_versions()
        assert len(result.items) == 1
        assert result.items[0].version == "cv1"

    def test_raises_client_error_on_404(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            status_code=404,
            content=b'{"error":{"code":"NOT_FOUND","message":"not found"}}',
        )
        with pytest.raises(CBCClientError):
            client.get_consumption_versions()

    def test_raises_server_error_on_500(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(status_code=500, content=b"")
        with pytest.raises(CBCServerError):
            client.get_consumption_versions()

    def test_raises_network_error_on_connection_failure(self):
        client, mock_http = _make_client()
        mock_http.request.side_effect = httpx.ConnectError("refused")
        with pytest.raises(CBCNetworkError):
            client.get_consumption_versions()


# ---------------------------------------------------------------------------
# DefaultClient — _get_configuration_objects
# ---------------------------------------------------------------------------


class TestGetConfigurationObjects:
    def test_returns_grouped_config_objects(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
                "items": [
                    {
                        "configurationObjectId": "payment-config",
                        "entities": [{"entityId": "payment-mode"}],
                    },
                    {
                        "configurationObjectId": "tax-config",
                        "entities": [
                            {"entityId": "tax-category"},
                            {"entityId": "tax-rate"},
                        ],
                    },
                ]
            }
        )
        result = client._get_configuration_objects(
            "https://cbc.example.ondemand.com", "app-tenant", "cv1"
        )
        assert len(result.items) == 2
        assert result.items[0].config_object_id == "payment-config"
        assert [e.entity_id for e in result.items[1].entities] == [
            "tax-category",
            "tax-rate",
        ]


# ---------------------------------------------------------------------------
# DefaultClient — _fetch_entity_data
# ---------------------------------------------------------------------------


class TestFetchEntityData:
    def test_reads_array_content_items(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
                "metadata": {
                    "entityName": "tax-category",
                    "configurationObjectId": "tax-config",
                },
                "contentShape": "ARRAY",
                "content": {"items": [{"code": "STD"}], "adaptedKeys": []},
            }
        )
        result = client._fetch_entity_data(
            "https://cbc.example.ondemand.com",
            "app-tenant",
            "cv1",
            "tax-config",
            "tax-category",
        )
        assert result.entity_id == "tax-category"
        assert result.data.as_list() == [{"code": "STD"}]

    def test_reads_object_content_item(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
                "metadata": {
                    "entityName": "globalSettings",
                    "configurationObjectId": "pmc-settings",
                },
                "contentShape": "OBJECT",
                "content": {"item": {"maxRetries": 3, "timeoutSeconds": 30}},
            }
        )
        result = client._fetch_entity_data(
            "https://cbc.example.ondemand.com",
            "app-tenant",
            "cv1",
            "pmc-settings",
            "globalSettings",
        )
        assert result.entity_id == "globalSettings"
        assert result.data.as_object() == {"maxRetries": 3, "timeoutSeconds": 30}

    def test_defaults_to_empty_list_when_content_absent(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={"metadata": {"entityName": "policy"}, "contentShape": "ARRAY"}
        )
        result = client._fetch_entity_data(
            "https://cbc.example.ondemand.com",
            "app-tenant",
            "cv1",
            "policy-config",
            "policy",
        )
        assert result.data.as_list() == []

    def test_falls_back_to_path_entity_id_without_metadata(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={"contentShape": "ARRAY", "content": {"items": []}}
        )
        result = client._fetch_entity_data(
            "https://cbc.example.ondemand.com",
            "app-tenant",
            "cv1",
            "tax-config",
            "tax-rate",
        )
        assert result.entity_id == "tax-rate"


# ---------------------------------------------------------------------------
# DefaultClient — get_configuration
# ---------------------------------------------------------------------------


class TestGetConfiguration:
    def test_resolves_latest_version_when_none_given(self):
        client, mock_http = _make_client()
        versions_response = _mock_response(json_body={"items": [{"version": "v2"}]})
        config_objects_response = _mock_response(json_body={"items": []})
        mock_http.request.side_effect = [versions_response, config_objects_response]

        result = client.get_configuration()
        assert isinstance(result, ConfigData)
        assert result.consumption_version == "v2"
        assert result.config_objects == []

    def test_raises_runtime_error_when_no_versions_exist(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(json_body={"items": []})
        with pytest.raises(CBCClientError, match="no consumption version"):
            client.get_configuration()

    def test_uses_explicit_consumption_version(self):
        client, mock_http = _make_client()
        config_objects_response = _mock_response(
            json_body={
                "items": [
                    {
                        "configurationObjectId": "payment-config",
                        "entities": [{"entityId": "payment-mode"}],
                    }
                ]
            }
        )
        data_response = _mock_response(
            json_body={
                "metadata": {"entityName": "payment-mode"},
                "contentShape": "ARRAY",
                "content": {"items": [{"k": "v"}]},
            }
        )
        mock_http.request.side_effect = [config_objects_response, data_response]

        result = client.get_configuration(consumption_version="cv1")
        assert len(result.config_objects) == 1
        assert result.config_objects[0].config_object_id == "payment-config"
        assert len(result.config_objects[0].entities) == 1
        assert result.config_objects[0].entities[0].entity_id == "payment-mode"

    def test_resolves_base_url_once_per_call(self):
        """One get_configuration resolves base_url once, not per HTTP request."""
        call_count = 0

        def base_url_fn() -> str:
            nonlocal call_count
            call_count += 1
            return "https://cbc.example.ondemand.com"

        mock_http = MagicMock(spec=httpx.Client)
        client = DefaultClient(
            base_url=base_url_fn,
            app_tenant_id=_app_tid(),
            http_client=mock_http,
        )
        config_objects_response = _mock_response(
            json_body={
                "items": [
                    {
                        "configurationObjectId": "tax-config",
                        "entities": [
                            {"entityId": "tax-category"},
                            {"entityId": "tax-rate"},
                        ],
                    }
                ]
            }
        )
        data_response = _mock_response(
            json_body={"contentShape": "ARRAY", "content": {"items": []}}
        )
        # config-objects + 2 entity-data requests = 3 HTTP calls, 1 base_url resolve
        mock_http.request.side_effect = [
            config_objects_response,
            data_response,
            data_response,
        ]

        client.get_configuration(consumption_version="cv1")
        assert call_count == 1


# ---------------------------------------------------------------------------
# DefaultClient — context manager
# ---------------------------------------------------------------------------


class TestDefaultClientContextManager:
    def test_close_called_on_exit(self):
        client, mock_http = _make_client()
        with client:
            pass
        mock_http.close.assert_called_once()


# ---------------------------------------------------------------------------
# create_client
# ---------------------------------------------------------------------------


class TestCreateClient:
    def test_returns_default_client(self):
        client = create_client(
            base_url=lambda: "http://localhost:8001",
            app_tenant_id=lambda: "app-t1",
        )
        assert isinstance(client, DefaultClient)

    def test_passes_ssl_context_through(self):
        import ssl

        ctx = ssl.create_default_context()
        client = create_client(
            base_url=lambda: "https://cbc.example.ondemand.com",
            app_tenant_id=lambda: "app-t1",
            ssl_context=ctx,
        )
        assert isinstance(client, DefaultClient)
