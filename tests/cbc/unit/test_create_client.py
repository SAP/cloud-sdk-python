"""Unit tests for the default platform resolvers and create_client's wiring.

These cover the behaviour that used to live in the platform adapter: resolving
``app_tenant_id`` / ``base_url`` from the SDK runtime context, loading the mTLS
certificate from the Destination Service, and the config → env → platform-default
precedence that ``create_client`` applies when a :class:`CBCConfig` axis is unset.
"""

from __future__ import annotations

import ssl
from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.cbc.client import (
    CBC_FRAGMENT_PREFIX,
    ENV_CERT_NAME,
    ENV_DESTINATION_INSTANCE,
    ENV_LANDSCAPE,
    CBCClient,
    _load_ssl_context,
    _resolve_app_tenant_id,
    _resolve_base_url,
    create_client,
)
from sap_cloud_sdk.cbc.config import CBCConfig
from sap_cloud_sdk.cbc.exceptions import CBCConfigError
from sap_cloud_sdk.core.runtime_context import APP_TENANT_ID, DWC_SUBDOMAIN
from sap_cloud_sdk.core.runtime_context._context import RuntimeContext, set_context
from sap_cloud_sdk.destination import AccessStrategy


@pytest.fixture(autouse=True)
def _reset_runtime_context():
    """Each test starts from an empty runtime context."""
    set_context(RuntimeContext())
    yield
    set_context(RuntimeContext())


def _seed_context(app_tenant_id: str = "", subdomain: str = "") -> None:
    values = {}
    if app_tenant_id:
        values[APP_TENANT_ID] = app_tenant_id
    if subdomain:
        values[DWC_SUBDOMAIN] = subdomain
    set_context(RuntimeContext(values))


# ---------------------------------------------------------------------------
# _resolve_app_tenant_id
# ---------------------------------------------------------------------------


class TestResolveAppTenantId:
    def test_resolve_app_tenant_id_with_context_value_returns_it(self):
        _seed_context(app_tenant_id="app-t1")
        assert _resolve_app_tenant_id() == "app-t1"

    def test_resolve_app_tenant_id_with_empty_context_raises_cbc_config_error(self):
        with pytest.raises(CBCConfigError, match="app tenant id"):
            _resolve_app_tenant_id()


# ---------------------------------------------------------------------------
# _resolve_base_url
# ---------------------------------------------------------------------------


class TestResolveBaseUrl:
    def test_resolve_base_url_with_matching_fragment_returns_cbc_url(self):
        _seed_context(app_tenant_id="app-t1", subdomain="appfnd-subscriber")
        match = MagicMock()
        match.name = f"{CBC_FRAGMENT_PREFIX}appfnd-subscriber"
        match.properties = {
            "appTenantId": "app-t1",
            "cbcUrl": "https://cbc.example.cloud.sap",
        }
        fake_client = MagicMock()
        fake_client.get_subaccount_fragment.return_value = match

        with patch(
            "sap_cloud_sdk.destination.create_fragment_client",
            return_value=fake_client,
        ):
            url = _resolve_base_url("default")

        assert url == "https://cbc.example.cloud.sap"
        fake_client.get_subaccount_fragment.assert_called_once_with(
            f"{CBC_FRAGMENT_PREFIX}appfnd-subscriber",
            access_strategy=AccessStrategy.SUBSCRIBER_ONLY,
            tenant="appfnd-subscriber",
        )

    def test_resolve_base_url_with_empty_subdomain_raises_cbc_config_error(self):
        _seed_context(app_tenant_id="app-t1")
        with pytest.raises(CBCConfigError, match="subdomain"):
            _resolve_base_url("default")

    def test_resolve_base_url_with_no_matching_fragment_raises_cbc_config_error(self):
        _seed_context(app_tenant_id="app-t1", subdomain="appfnd-subscriber")
        fake_client = MagicMock()
        fake_client.get_subaccount_fragment.return_value = None
        with patch(
            "sap_cloud_sdk.destination.create_fragment_client",
            return_value=fake_client,
        ):
            with pytest.raises(CBCConfigError, match="No CBC mapping fragment"):
                _resolve_base_url("default")

    def test_resolve_base_url_with_fragment_missing_cbc_url_raises_cbc_config_error(self):
        _seed_context(app_tenant_id="app-t1", subdomain="appfnd-subscriber")
        match = MagicMock()
        match.name = f"{CBC_FRAGMENT_PREFIX}appfnd-subscriber"
        match.properties = {"appTenantId": "app-t1"}
        fake_client = MagicMock()
        fake_client.get_subaccount_fragment.return_value = match
        with patch(
            "sap_cloud_sdk.destination.create_fragment_client",
            return_value=fake_client,
        ):
            with pytest.raises(CBCConfigError, match="no 'cbcUrl'"):
                _resolve_base_url("default")

    def test_resolve_base_url_when_destination_raises_wraps_as_cbc_config_error(self):
        from sap_cloud_sdk.destination.exceptions import DestinationOperationError

        _seed_context(app_tenant_id="app-t1", subdomain="appfnd-subscriber")
        fake_client = MagicMock()
        fake_client.get_subaccount_fragment.side_effect = DestinationOperationError(
            "failed to get fragment: token error"
        )
        with patch(
            "sap_cloud_sdk.destination.create_fragment_client",
            return_value=fake_client,
        ):
            with pytest.raises(CBCConfigError, match="Could not resolve the CBC URL"):
                _resolve_base_url("default")


# ---------------------------------------------------------------------------
# _load_ssl_context
# ---------------------------------------------------------------------------


class TestLoadSslContext:
    def test_load_ssl_context_with_valid_cert_returns_ssl_context(self):
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

    def test_load_ssl_context_when_cert_not_found_raises_cbc_config_error(self):
        fake_cert_client = MagicMock()
        fake_cert_client.get_subaccount_certificate.return_value = None
        with patch(
            "sap_cloud_sdk.destination.create_certificate_client",
            return_value=fake_cert_client,
        ):
            with pytest.raises(CBCConfigError, match="not found"):
                _load_ssl_context("default", "missing.pem", None)

    def test_load_ssl_context_when_destination_raises_wraps_as_cbc_config_error(self):
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
                _load_ssl_context("default", "my-cert.pem", None)


# ---------------------------------------------------------------------------
# create_client — default wiring (infer from provisioning) + precedence
# ---------------------------------------------------------------------------


class TestCreateClientDefaults:
    def test_default_wiring_with_landscape_env_builds_ssl_context_from_cert(self, monkeypatch):
        monkeypatch.setenv(ENV_LANDSCAPE, "cbc-fndtst-dev-eu12")
        with patch(
            "sap_cloud_sdk.cbc.client._load_ssl_context",
            return_value=ssl.create_default_context(),
        ) as load:
            client = create_client()
            assert isinstance(client, CBCClient)
            # The factory is resolved once at construction to build the mTLS client.
            load.assert_called_once()
            instance_arg, cert_arg, _pw = load.call_args.args
            assert instance_arg == "default"
            assert cert_arg == "sap-managed-runtime-ias-cbc-fndtst-dev-eu12.pem"
            # The factory is re-invokable (used again on a TLS failure to reload).
            assert client._ssl_factory is not None
            client._ssl_factory()
            assert load.call_count == 2

    def test_env_overrides_apply_instance_and_cert_name(self, monkeypatch):
        monkeypatch.setenv(ENV_DESTINATION_INSTANCE, "cbc-instance")
        monkeypatch.setenv(ENV_CERT_NAME, "my-cert.pem")
        with patch(
            "sap_cloud_sdk.cbc.client._load_ssl_context",
            return_value=ssl.create_default_context(),
        ) as load:
            create_client()
        instance_arg, cert_arg, _pw = load.call_args.args
        assert instance_arg == "cbc-instance"
        assert cert_arg == "my-cert.pem"

    def test_config_object_applies_instance_and_cert_name(self):
        with patch(
            "sap_cloud_sdk.cbc.client._load_ssl_context",
            return_value=ssl.create_default_context(),
        ) as load:
            create_client(
                CBCConfig(
                    destination_instance="cbc-instance",
                    cbc_cert_name="my-cert.pem",
                )
            )
        instance_arg, cert_arg, _pw = load.call_args.args
        assert instance_arg == "cbc-instance"
        assert cert_arg == "my-cert.pem"

    def test_config_value_wins_over_env(self, monkeypatch):
        monkeypatch.setenv(ENV_DESTINATION_INSTANCE, "from-env")
        monkeypatch.setenv(ENV_CERT_NAME, "from-env.pem")
        with patch(
            "sap_cloud_sdk.cbc.client._load_ssl_context",
            return_value=ssl.create_default_context(),
        ) as load:
            create_client(
                CBCConfig(
                    destination_instance="from-config",
                    cbc_cert_name="from-config.pem",
                )
            )
        instance_arg, cert_arg, _pw = load.call_args.args
        assert instance_arg == "from-config"
        assert cert_arg == "from-config.pem"

    def test_without_landscape_or_cert_name_raises_cbc_config_error(self, monkeypatch):
        monkeypatch.delenv(ENV_LANDSCAPE, raising=False)
        monkeypatch.delenv(ENV_CERT_NAME, raising=False)
        with pytest.raises(CBCConfigError, match=ENV_LANDSCAPE):
            create_client()

    def test_default_resolvers_read_runtime_context_at_request_time(self, monkeypatch):
        """With no overrides, base_url + app_tenant_id come from the runtime context."""
        monkeypatch.setenv(ENV_CERT_NAME, "my-cert.pem")
        with patch(
            "sap_cloud_sdk.cbc.client._load_ssl_context",
            return_value=ssl.create_default_context(),
        ):
            client = create_client()
        assert isinstance(client, CBCClient)

        _seed_context(app_tenant_id="app-t1", subdomain="appfnd-subscriber")
        assert client._resolve_app_tenant_id() == "app-t1"

        fragment = MagicMock()
        fragment.name = f"{CBC_FRAGMENT_PREFIX}appfnd-subscriber"
        fragment.properties = {
            "appTenantId": "app-t1",
            "cbcUrl": "https://cbc.example.cloud.sap",
        }
        fake_fc = MagicMock()
        fake_fc.get_subaccount_fragment.return_value = fragment
        with patch(
            "sap_cloud_sdk.destination.create_fragment_client", return_value=fake_fc
        ):
            assert client._base_url() == "https://cbc.example.cloud.sap"
