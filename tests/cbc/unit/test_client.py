"""Unit tests for DefaultClient and client_from_env."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import json
import pytest

from sap_cloud_sdk.cbc.client import DefaultClient, create_client
from sap_cloud_sdk.cbc.config import ENV_URL, ENV_CERT_PATH, ENV_KEY_PATH
from sap_cloud_sdk.cbc.exceptions import (
    CBCClientError,
    CBCConfigError,
    CBCNetworkError,
    CBCServerError,
)
from sap_cloud_sdk.cbc._models import (
    ConfigData,
    TenantContext,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tenant(cbc: str = "cbc-tenant", app: str = "app-tenant") -> TenantContext:
    return TenantContext(cbcTenantId=cbc, appTenantId=app)


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
) -> tuple[DefaultClient, MagicMock]:
    mock_http = MagicMock(spec=httpx.Client)
    client = DefaultClient(base_url=base_url, http_client=mock_http)
    return client, mock_http


# ---------------------------------------------------------------------------
# DefaultClient — URL detection
# ---------------------------------------------------------------------------


class TestDefaultClientLocalMode:
    def test_loopback_localhost_disables_subdomain_replacement(self):
        client, _ = _make_client("http://localhost:8001")
        assert not client._config.replace_subdomain

    def test_loopback_127_disables_subdomain_replacement(self):
        client, _ = _make_client("http://127.0.0.1:8001")
        assert not client._config.replace_subdomain

    def test_production_url_enables_subdomain_replacement(self):
        client, _ = _make_client("https://cbc.example.ondemand.com")
        assert client._config.replace_subdomain


# ---------------------------------------------------------------------------
# DefaultClient — URL building
# ---------------------------------------------------------------------------


class TestConfigurationsUrl:
    def test_production_replaces_subdomain_with_tenant(self):
        client, _ = _make_client("https://cbc.example.ondemand.com")
        url = client._configurations_url(_tenant("my-tenant"), "/consumptionVersions")
        assert url.startswith("https://my-tenant.")

    def test_local_does_not_replace_subdomain(self):
        client, _ = _make_client("http://localhost:8001")
        url = client._configurations_url(_tenant("my-tenant"), "/consumptionVersions")
        assert "localhost:8001" in url
        assert "my-tenant" not in url.split("//")[1].split("/")[0]


# ---------------------------------------------------------------------------
# DefaultClient — get_consumption_versions
# ---------------------------------------------------------------------------


class TestGetConsumptionVersions:
    def test_returns_parsed_versions(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={"items": [{"version": "cv1"}]}
        )
        result = client.get_consumption_versions(_tenant())
        assert len(result.items) == 1
        assert result.items[0].version == "cv1"

    def test_raises_client_error_on_404(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            status_code=404,
            content=b'{"error":{"code":"NOT_FOUND","message":"not found"}}',
        )
        with pytest.raises(CBCClientError):
            client.get_consumption_versions(_tenant())

    def test_raises_server_error_on_500(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(status_code=500, content=b"")
        with pytest.raises(CBCServerError):
            client.get_consumption_versions(_tenant())

    def test_raises_network_error_on_connection_failure(self):
        client, mock_http = _make_client()
        mock_http.request.side_effect = httpx.ConnectError("refused")
        with pytest.raises(CBCNetworkError):
            client.get_consumption_versions(_tenant())


# ---------------------------------------------------------------------------
# DefaultClient — _get_entities
# ---------------------------------------------------------------------------


class TestGetEntities:
    def test_returns_parsed_entities(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
                "items": [
                    {
                        "entityId": "i1",
                        "entityName": "payment-mode",
                        "configurationObjectId": "payment-config",
                    }
                ]
            }
        )
        result = client._get_entities(_tenant(), "cv1")
        assert len(result.items) == 1
        assert result.items[0].internal_id == "i1"


# ---------------------------------------------------------------------------
# DefaultClient — _get_entity_data
# ---------------------------------------------------------------------------


class TestGetEntityData:
    def test_returns_entity_data_with_entity_id(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={"items": [{"key": "value"}]}
        )

        result = client._get_entity_data(_tenant(), "cv1", "e1")
        assert result.entity_id == "e1"
        assert result.data.as_list() == [{"key": "value"}]

    def test_uses_api_metadata_entity_name_when_present(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
                "metadata": {
                    "entityName": "rules",
                    "configurationObjectId": "qualification-rules",
                },
                "items": [{"key": "value"}],
            }
        )

        result = client._get_entity_data(_tenant(), "cv1", "e1")
        assert result.entity_id == "rules"
        assert result.data.as_list() == [{"key": "value"}]

    def test_handles_flat_list_response(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(json_body=[{"row": 1}])

        result = client._get_entity_data(_tenant(), "cv1", "e1")
        assert result.data.as_list() == [{"row": 1}]


# ---------------------------------------------------------------------------
# DefaultClient — get_configuration
# ---------------------------------------------------------------------------


class TestGetConfiguration:
    def test_resolves_latest_version_when_none_given(self):
        client, mock_http = _make_client()
        versions_response = _mock_response(json_body={"items": [{"version": "v2"}]})
        entities_response = _mock_response(json_body={"items": []})
        mock_http.request.side_effect = [versions_response, entities_response]

        result = client.get_configuration(_tenant())
        assert isinstance(result, ConfigData)
        assert result.consumption_version == "v2"
        assert result.config_objects == []

    def test_raises_runtime_error_when_no_versions_exist(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(json_body={"items": []})
        with pytest.raises(CBCClientError, match="no consumption version"):
            client.get_configuration(_tenant())

    def test_uses_explicit_consumption_version(self):
        client, mock_http = _make_client()
        entities_response = _mock_response(
            json_body={
                "items": [
                    {
                        "entityId": "i1",
                        "entityName": "payment-mode",
                        "configurationObjectId": "payment-config",
                    }
                ]
            }
        )
        data_response = _mock_response(json_body={"items": [{"k": "v"}]})
        mock_http.request.side_effect = [entities_response, data_response]

        result = client.get_configuration(_tenant(), consumption_version="cv1")
        assert len(result.config_objects) == 1
        assert result.config_objects[0].config_object_id == "payment-config"
        assert len(result.config_objects[0].entities) == 1


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
# create_client / load_from_env
# ---------------------------------------------------------------------------


class TestCreateClient:
    def test_raises_config_error_when_no_env_vars(self, monkeypatch):
        monkeypatch.delenv(ENV_URL, raising=False)
        monkeypatch.delenv(ENV_CERT_PATH, raising=False)
        monkeypatch.delenv(ENV_KEY_PATH, raising=False)
        with pytest.raises(CBCConfigError):
            create_client()

    def test_returns_client_for_loopback_url(self, monkeypatch):
        monkeypatch.setenv(ENV_URL, "http://localhost:8001")
        monkeypatch.delenv(ENV_CERT_PATH, raising=False)
        monkeypatch.delenv(ENV_KEY_PATH, raising=False)
        client = create_client()
        assert isinstance(client, DefaultClient)

    def test_raises_config_error_for_incomplete_triplet(self, monkeypatch, tmp_path):
        cert = tmp_path / "tls.crt"
        cert.write_text("cert")
        monkeypatch.setenv(ENV_CERT_PATH, str(cert))
        monkeypatch.delenv(ENV_KEY_PATH, raising=False)
        monkeypatch.delenv(ENV_URL, raising=False)
        with pytest.raises(CBCConfigError, match="incomplete"):
            create_client()

    def test_raises_config_error_for_missing_cert_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv(ENV_CERT_PATH, str(tmp_path / "missing.crt"))
        with pytest.raises(CBCConfigError, match="does not exist"):
            create_client()

    def test_returns_client_with_env_var_cert_triplet(self, monkeypatch, tmp_path):
        cert = tmp_path / "tls.crt"
        key = tmp_path / "tls.key"
        cert.write_text("cert")
        key.write_text("key")
        monkeypatch.setenv(ENV_CERT_PATH, str(cert))
        monkeypatch.setenv(ENV_KEY_PATH, str(key))
        monkeypatch.setenv(ENV_URL, "https://cbc.example.ondemand.com")
        client = create_client()
        assert isinstance(client, DefaultClient)

    def test_accepts_explicit_config(self):
        from sap_cloud_sdk.cbc.config import CBCConfig

        cfg = CBCConfig(base_url="http://localhost:9000")
        client = create_client(config=cfg)
        assert isinstance(client, DefaultClient)
