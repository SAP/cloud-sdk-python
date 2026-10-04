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
    app_tenant_id_var,
    create_agent_client,
    load_ssl_context,
    resolve_app_tenant_id,
    resolve_base_url,
    tenant_subdomain_var,
)
from sap_cloud_sdk.cbc.client import DefaultClient, create_client
from sap_cloud_sdk.cbc.exceptions import CBCConfigError


@pytest.fixture(autouse=True)
def _reset_contextvars():
    app_tenant_id_var.set("")
    tenant_subdomain_var.set("")
    yield


# ---------------------------------------------------------------------------
# resolve_app_tenant_id
# ---------------------------------------------------------------------------


class TestResolveAppTenantId:
    def test_returns_contextvar_value(self):
        app_tenant_id_var.set("app-t1")
        assert resolve_app_tenant_id() == "app-t1"

    def test_raises_when_empty(self):
        with pytest.raises(CBCConfigError, match="cbc_app_tenant_id"):
            resolve_app_tenant_id()


# ---------------------------------------------------------------------------
# resolve_base_url
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
            url = resolve_base_url("default")

        assert url == "https://cbc.example.cloud.sap"
        fake_client.list_subaccount_fragments.assert_called_once_with(
            tenant="appfnd-subscriber"
        )

    def test_raises_when_subdomain_empty(self):
        app_tenant_id_var.set("app-t1")
        with pytest.raises(CBCConfigError, match="cbc_tenant_subdomain"):
            resolve_base_url("default")

    def test_raises_when_app_tenant_id_empty(self):
        tenant_subdomain_var.set("appfnd-subscriber")
        with pytest.raises(CBCConfigError, match="cbc_app_tenant_id"):
            resolve_base_url("default")

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
                resolve_base_url("default")

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
                resolve_base_url("default")

    def test_wraps_destination_error_as_config_error(self):
        from sap_cloud_sdk.destination.exceptions import DestinationOperationError

        tenant_subdomain_var.set("appfnd-subscriber")
        app_tenant_id_var.set("app-t1")
        fake_client = MagicMock()
        fake_client.list_subaccount_fragments.side_effect = DestinationOperationError(
            "failed to list subaccount fragments: token error"
        )
        with patch(
            "sap_cloud_sdk.destination.create_fragment_client",
            return_value=fake_client,
        ):
            with pytest.raises(CBCConfigError, match="Could not resolve the CBC URL"):
                resolve_base_url("default")


# ---------------------------------------------------------------------------
# load_ssl_context
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
            result = load_ssl_context("default", "my-cert.pem", b"secret")

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
                load_ssl_context("default", "missing.pem", None)

    def test_wraps_destination_error_as_config_error(self):
        from sap_cloud_sdk.destination.exceptions import DestinationOperationError

        fake_cert_client = MagicMock()
        fake_cert_client.get_subaccount_certificate.side_effect = (
            DestinationOperationError("token error")
        )
        with patch(
            "sap_cloud_sdk.destination.create_certificate_client",
            return_value=fake_cert_client,
        ):
            with pytest.raises(
                CBCConfigError, match="Could not fetch the mTLS certificate"
            ):
                load_ssl_context("default", "my-cert.pem", None)


# ---------------------------------------------------------------------------
# create_agent_client
# ---------------------------------------------------------------------------


class TestCreateAgentClient:
    def test_builds_ssl_context_from_cert_default(self, monkeypatch):
        monkeypatch.setenv(ENV_LANDSCAPE, "cbc-fndtst-dev-eu12")
        with patch(
            "sap_cloud_sdk.cbc.client_adapter.load_ssl_context",
            return_value=ssl.create_default_context(),
        ) as load:
            client = create_agent_client()
            # The adapter wires a factory that resolves the cert; the core
            # invokes it once at construction to build the mTLS client.
            load.assert_called_once()
            instance_arg, cert_arg, _pw = load.call_args.args
            assert instance_arg == "default"
            assert cert_arg == "sap-managed-runtime-ias-cbc-fndtst-dev-eu12.pem"
            # The factory is re-invokable (used again on a TLS failure to reload).
            client._ssl_factory()
            assert load.call_count == 2
        assert isinstance(client, DefaultClient)

    def test_env_overrides_apply(self, monkeypatch):
        monkeypatch.setenv(ENV_DESTINATION_INSTANCE, "cbc-instance")
        monkeypatch.setenv(ENV_CERT_NAME, "my-cert.pem")
        with patch(
            "sap_cloud_sdk.cbc.client_adapter.load_ssl_context",
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
        monkeypatch.setenv(ENV_CERT_NAME, "my-cert.pem")
        with patch(
            "sap_cloud_sdk.cbc.client_adapter.load_ssl_context",
            return_value=ssl.create_default_context(),
        ):
            client = create_agent_client()

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


# ---------------------------------------------------------------------------
# Compose path — public resolvers + create_client (override one axis)
# ---------------------------------------------------------------------------


class TestComposeWithPublicResolvers:
    def test_compose_core_with_public_resolvers(self):
        """Advanced callers keep platform base_url + app_tenant_id but bring
        their own mTLS context, composing the public resolvers with the core."""
        client = create_client(
            base_url=lambda: resolve_base_url("default"),
            app_tenant_id=resolve_app_tenant_id,
            ssl_context=lambda: ssl.create_default_context(),
        )
        assert isinstance(client, DefaultClient)
