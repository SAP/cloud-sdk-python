"""Unit tests for the CBC platform adapter."""

from __future__ import annotations

import ssl
from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.cbc.client_adapter import (
    CBC_FRAGMENT_PREFIX,
    ENV_CERT_NAME,
    ENV_DESTINATION_INSTANCE,
    ENV_LANDSCAPE,
    _resolve_app_tenant_id,
    _resolve_base_url,
    _load_ssl_context,
    app_tenant_id_var,
    create_agent_client,
    tenant_subdomain_var,
)
from sap_cloud_sdk.cbc.client import DefaultClient
from sap_cloud_sdk.cbc.exceptions import CBCConfigError


@pytest.fixture(autouse=True)
def _reset_contextvars():
    app_tenant_id_var.set("")
    tenant_subdomain_var.set("")
    yield


# ---------------------------------------------------------------------------
# _resolve_app_tenant_id
# ---------------------------------------------------------------------------


class TestResolveAppTenantId:
    def test_returns_contextvar_value(self):
        app_tenant_id_var.set("app-t1")
        assert _resolve_app_tenant_id() == "app-t1"

    def test_raises_when_empty(self):
        with pytest.raises(CBCConfigError, match="cbc_app_tenant_id"):
            _resolve_app_tenant_id()


# ---------------------------------------------------------------------------
# _resolve_base_url
# ---------------------------------------------------------------------------


class TestResolveBaseUrl:
    def test_reads_cbc_url_from_matching_fragment(self):
        tenant_subdomain_var.set("appfnd-subscriber")
        app_tenant_id_var.set("app-t1")
        other = MagicMock()
        other.name = f"{CBC_FRAGMENT_PREFIX}cbc-other"
        other.properties = {"appTenantId": "app-other", "cbcUrl": "https://nope"}
        match = MagicMock()
        match.name = f"{CBC_FRAGMENT_PREFIX}cbc-t1"
        match.properties = {
            "appTenantId": "app-t1",
            "cbcUrl": "https://cbc.example.cloud.sap",
        }
        fake_client = MagicMock()
        fake_client.list_subaccount_fragments.return_value = [other, match]

        with patch(
            "sap_cloud_sdk.destination.create_fragment_client",
            return_value=fake_client,
        ):
            url = _resolve_base_url("default")

        assert url == "https://cbc.example.cloud.sap"
        fake_client.list_subaccount_fragments.assert_called_once_with(
            tenant="appfnd-subscriber"
        )

    def test_raises_when_subdomain_empty(self):
        app_tenant_id_var.set("app-t1")
        with pytest.raises(CBCConfigError, match="cbc_tenant_subdomain"):
            _resolve_base_url("default")

    def test_raises_when_app_tenant_id_empty(self):
        tenant_subdomain_var.set("appfnd-subscriber")
        with pytest.raises(CBCConfigError, match="cbc_app_tenant_id"):
            _resolve_base_url("default")

    def test_raises_when_no_matching_fragment(self):
        tenant_subdomain_var.set("appfnd-subscriber")
        app_tenant_id_var.set("app-t1")
        other = MagicMock()
        other.name = f"{CBC_FRAGMENT_PREFIX}cbc-other"
        other.properties = {"appTenantId": "app-other", "cbcUrl": "https://nope"}
        fake_client = MagicMock()
        fake_client.list_subaccount_fragments.return_value = [other]
        with patch(
            "sap_cloud_sdk.destination.create_fragment_client",
            return_value=fake_client,
        ):
            with pytest.raises(CBCConfigError, match="No CBC mapping fragment"):
                _resolve_base_url("default")

    def test_raises_when_cbc_url_missing_from_fragment(self):
        tenant_subdomain_var.set("appfnd-subscriber")
        app_tenant_id_var.set("app-t1")
        match = MagicMock()
        match.name = f"{CBC_FRAGMENT_PREFIX}cbc-t1"
        match.properties = {"appTenantId": "app-t1"}
        fake_client = MagicMock()
        fake_client.list_subaccount_fragments.return_value = [match]
        with patch(
            "sap_cloud_sdk.destination.create_fragment_client",
            return_value=fake_client,
        ):
            with pytest.raises(CBCConfigError, match="no 'cbcUrl'"):
                _resolve_base_url("default")


# ---------------------------------------------------------------------------
# _load_ssl_context
# ---------------------------------------------------------------------------


class TestLoadSslContext:
    def test_loads_cert_into_ssl_context(self):
        ctx = ssl.create_default_context()
        cert = MagicMock()
        cert.content = "<pem>"
        cert.name = "my-cert.pem"
        fake_cert_client = MagicMock()
        fake_cert_client.get_subaccount_certificate.return_value = cert

        with (
            patch(
                "sap_cloud_sdk.destination.create_certificate_client",
                return_value=fake_cert_client,
            ),
            patch(
                "sap_cloud_sdk.destination._cert_loader._load_pem",
                return_value=ctx,
            ) as load_pem,
        ):
            result = _load_ssl_context("default", "my-cert.pem", b"secret")

        assert result is ctx
        load_pem.assert_called_once_with("<pem>", b"secret", "my-cert.pem")

    def test_raises_when_cert_not_found(self):
        fake_cert_client = MagicMock()
        fake_cert_client.get_subaccount_certificate.return_value = None
        with patch(
            "sap_cloud_sdk.destination.create_certificate_client",
            return_value=fake_cert_client,
        ):
            with pytest.raises(CBCConfigError, match="not found"):
                _load_ssl_context("default", "missing.pem", None)


# ---------------------------------------------------------------------------
# create_agent_client
# ---------------------------------------------------------------------------


class TestCreateAgentClient:
    def test_explicit_ssl_context_short_circuits_cert_load(self):
        ctx = ssl.create_default_context()
        with patch("sap_cloud_sdk.cbc.client_adapter._load_ssl_context") as load:
            client = create_agent_client(ssl_context=ctx)
        load.assert_not_called()
        assert isinstance(client, DefaultClient)

    def test_builds_ssl_context_from_cert_default(self, monkeypatch):
        monkeypatch.setenv(ENV_LANDSCAPE, "cbc-fndtst-dev-eu12")
        with patch(
            "sap_cloud_sdk.cbc.client_adapter._load_ssl_context",
            return_value=ssl.create_default_context(),
        ) as load:
            client = create_agent_client()
        load.assert_called_once()
        instance_arg, cert_arg, _pw = load.call_args.args
        assert instance_arg == "default"
        assert cert_arg == "sap-managed-runtime-ias-cbc-fndtst-dev-eu12.pem"
        assert isinstance(client, DefaultClient)

    def test_env_overrides_apply(self, monkeypatch):
        monkeypatch.setenv(ENV_DESTINATION_INSTANCE, "cbc-instance")
        monkeypatch.setenv(ENV_CERT_NAME, "my-cert.pem")
        with patch(
            "sap_cloud_sdk.cbc.client_adapter._load_ssl_context",
            return_value=ssl.create_default_context(),
        ) as load:
            create_agent_client()
        instance_arg, cert_arg, _pw = load.call_args.args
        assert instance_arg == "cbc-instance"
        assert cert_arg == "my-cert.pem"

    def test_raises_when_landscape_unset_and_no_cert_name(self, monkeypatch):
        monkeypatch.delenv(ENV_LANDSCAPE, raising=False)
        monkeypatch.delenv(ENV_CERT_NAME, raising=False)
        with pytest.raises(CBCConfigError, match=ENV_LANDSCAPE):
            create_agent_client()

    def test_wires_resolvers_into_client(self, monkeypatch):
        """The two ContextVars drive base_url + app_tenant_id at request time."""
        ctx = ssl.create_default_context()
        client = create_agent_client(ssl_context=ctx)

        app_tenant_id_var.set("app-t1")
        assert client._resolve_app_tenant_id() == "app-t1"

        tenant_subdomain_var.set("appfnd-subscriber")
        fragment = MagicMock()
        fragment.name = f"{CBC_FRAGMENT_PREFIX}cbc-t1"
        fragment.properties = {
            "appTenantId": "app-t1",
            "cbcUrl": "https://cbc.example.cloud.sap",
        }
        fake_fc = MagicMock()
        fake_fc.list_subaccount_fragments.return_value = [fragment]
        with patch(
            "sap_cloud_sdk.destination.create_fragment_client", return_value=fake_fc
        ):
            assert client._base_url() == "https://cbc.example.cloud.sap"
