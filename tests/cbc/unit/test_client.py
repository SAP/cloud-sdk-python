"""Unit tests for CBCClient and create_client."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast
from unittest.mock import MagicMock

import httpx
import json
import pytest
import ssl

from sap_cloud_sdk.cbc.client import CBCClient, create_client, _is_tls_failure
from sap_cloud_sdk.cbc.config import CBCConfig
from sap_cloud_sdk.cbc.exceptions import (
    CBCClientError,
    CBCConfigError,
    CBCNetworkError,
    CBCServerError,
)
from sap_cloud_sdk.cbc._models import ConfigurationData, EntityData


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
) -> tuple[CBCClient, MagicMock]:
    mock_http = MagicMock(spec=httpx.Client)
    client = CBCClient(
        base_url=lambda: base_url,
        app_tenant_id=app_tenant_id or _app_tid(),
        http_client=mock_http,
    )
    return client, mock_http


# ---------------------------------------------------------------------------
# CBCClient — app_tenant_id callable
# ---------------------------------------------------------------------------


class TestAppTenantIdCallable:
    def test_app_tenant_id_callable_on_each_call_invokes_callable(self):
        call_count = 0

        def app_tenant_id_fn() -> str:
            nonlocal call_count
            call_count += 1
            return "app-tenant"

        mock_http = MagicMock(spec=httpx.Client)
        mock_http.request.return_value = _mock_response(
            json_body={"items": [{"version": "cv1"}]}
        )
        client = CBCClient(
            base_url=lambda: "https://cbc.example.ondemand.com",
            app_tenant_id=app_tenant_id_fn,
            http_client=mock_http,
        )
        client.get_consumption_versions()
        client.get_consumption_versions()
        assert call_count == 2


# ---------------------------------------------------------------------------
# CBCClient — URL building
# ---------------------------------------------------------------------------


class TestConfigurationsUrl:
    def test_configurations_url_with_base_and_suffix_joins_correctly(self):
        client, _ = _make_client("https://my-tenant.cbc.example.ondemand.com")
        url = client._configurations_url(
            "https://my-tenant.cbc.example.ondemand.com", "/consumptionVersions"
        )
        assert url == (
            "https://my-tenant.cbc.example.ondemand.com"
            "/configuration/v1/consumptionVersions"
        )


# ---------------------------------------------------------------------------
# CBCClient — get_consumption_versions
# ---------------------------------------------------------------------------


class TestGetConsumptionVersions:
    def test_get_consumption_versions_with_valid_response_returns_parsed_versions(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={"items": [{"version": "cv1"}]}
        )
        result = client.get_consumption_versions()
        assert len(result.items) == 1
        assert result.items[0].version == "cv1"

    def test_get_consumption_versions_on_404_raises_cbc_client_error(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            status_code=404,
            content=b'{"error":{"code":"NOT_FOUND","message":"not found"}}',
        )
        with pytest.raises(CBCClientError):
            client.get_consumption_versions()

    def test_get_consumption_versions_on_500_raises_cbc_server_error(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(status_code=500, content=b"")
        with pytest.raises(CBCServerError):
            client.get_consumption_versions()

    def test_get_consumption_versions_on_connection_failure_raises_cbc_network_error(
        self,
    ):
        client, mock_http = _make_client()
        mock_http.request.side_effect = httpx.ConnectError("refused")
        with pytest.raises(CBCNetworkError):
            client.get_consumption_versions()


# ---------------------------------------------------------------------------
# CBCClient — _get_configuration_objects
# ---------------------------------------------------------------------------


class TestGetConfigurationObjects:
    def test_get_configuration_objects_with_multiple_objects_returns_grouped_configuration_objects(
        self,
    ):
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
        assert result.items[0].configuration_object_id == "payment-config"
        assert [e.entity_id for e in result.items[1].entities] == [
            "tax-category",
            "tax-rate",
        ]


# ---------------------------------------------------------------------------
# CBCClient — _fetch_entity_data
# ---------------------------------------------------------------------------


class TestFetchEntityData:
    def test_fetch_entity_data_with_array_shape_returns_list_content(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
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

    def test_fetch_entity_data_with_object_shape_returns_dict_content(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
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

    def test_fetch_entity_data_with_absent_content_defaults_to_empty_list(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={"contentShape": "ARRAY"}
        )
        result = client._fetch_entity_data(
            "https://cbc.example.ondemand.com",
            "app-tenant",
            "cv1",
            "policy-config",
            "policy",
        )
        assert result.data.as_list() == []


# ---------------------------------------------------------------------------
# CBCClient — get_configuration
# ---------------------------------------------------------------------------


class TestGetConfiguration:
    def test_get_configuration_without_version_resolves_latest_and_returns_configuration_data(
        self,
    ):
        client, mock_http = _make_client()
        versions_response = _mock_response(json_body={"items": [{"version": "v2"}]})
        configuration_objects_response = _mock_response(json_body={"items": []})
        mock_http.request.side_effect = [
            versions_response,
            configuration_objects_response,
        ]

        result = client.get_configuration()
        assert isinstance(result, ConfigurationData)
        assert result.consumption_version == "v2"
        assert result.configuration_objects == []

    def test_get_configuration_when_no_versions_exist_raises_cbc_client_error(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(json_body={"items": []})
        with pytest.raises(CBCClientError, match="no consumption version"):
            client.get_configuration()

    def test_get_configuration_with_explicit_version_skips_version_resolution(self):
        client, mock_http = _make_client()
        configuration_objects_response = _mock_response(
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
                "contentShape": "ARRAY",
                "content": {"items": [{"k": "v"}]},
            }
        )
        mock_http.request.side_effect = [configuration_objects_response, data_response]

        result = client.get_configuration(consumption_version="cv1")
        assert len(result.configuration_objects) == 1
        assert (
            result.configuration_objects[0].configuration_object_id == "payment-config"
        )
        assert len(result.configuration_objects[0].entities) == 1
        assert result.configuration_objects[0].entities[0].entity_id == "payment-mode"

    def test_get_configuration_with_multiple_entities_resolves_base_url_once(self):
        """One get_configuration resolves base_url once, not per HTTP request."""
        call_count = 0

        def base_url_fn() -> str:
            nonlocal call_count
            call_count += 1
            return "https://cbc.example.ondemand.com"

        mock_http = MagicMock(spec=httpx.Client)
        client = CBCClient(
            base_url=base_url_fn,
            app_tenant_id=_app_tid(),
            http_client=mock_http,
        )
        configuration_objects_response = _mock_response(
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
            configuration_objects_response,
            data_response,
            data_response,
        ]

        client.get_configuration(consumption_version="cv1")
        assert call_count == 1


# ---------------------------------------------------------------------------
# CBCClient — get_entity_data
# ---------------------------------------------------------------------------


class TestGetEntityData:
    def test_get_entity_data_without_version_resolves_latest_and_returns_entity_data(
        self,
    ):
        client, mock_http = _make_client()
        versions_response = _mock_response(json_body={"items": [{"version": "v1"}]})
        entity_response = _mock_response(
            json_body={
                "contentShape": "ARRAY",
                "content": {"items": [{"code": "STD"}], "adaptedKeys": []},
            }
        )
        mock_http.request.side_effect = [versions_response, entity_response]

        result = client.get_entity_data("payment-config", "payment-mode")
        assert isinstance(result, EntityData)
        assert result.as_list() == [{"code": "STD"}]

    def test_get_entity_data_with_pinned_version_skips_version_resolution(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
                "contentShape": "OBJECT",
                "content": {"item": {"key": "value"}},
            }
        )

        result = client.get_entity_data(
            "agent-config", "settings", consumption_version="v42"
        )
        assert isinstance(result, EntityData)
        assert result.as_object() == {"key": "value"}
        # Only one HTTP call — no version resolution
        assert mock_http.request.call_count == 1

    def test_get_entity_data_when_no_versions_exist_raises_cbc_client_error(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(json_body={"items": []})
        with pytest.raises(CBCClientError, match="no consumption version"):
            client.get_entity_data("payment-config", "payment-mode")


# ---------------------------------------------------------------------------
# CBCClient — _features_url
# ---------------------------------------------------------------------------


class TestFeaturesUrl:
    def test_features_url_joins_base_feature_path_and_suffix(self):
        client, _ = _make_client("https://my-tenant.cbc.example.ondemand.com")
        url = client._features_url(
            "https://my-tenant.cbc.example.ondemand.com", "/features"
        )
        assert url == (
            "https://my-tenant.cbc.example.ondemand.com/feature/v1/features"
        )


# ---------------------------------------------------------------------------
# CBCClient — get_feature_statuses
# ---------------------------------------------------------------------------


class TestGetFeatureStatuses:
    def test_get_feature_statuses_returns_parsed_features(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
                "features": [
                    {"featureId": "ai_assisted_supplier_bid_analysis", "enabled": True},
                    {"featureId": "ai_assisted_tco_analysis", "enabled": False},
                ]
            }
        )
        result = client.get_feature_statuses()
        assert result.is_enabled("ai_assisted_supplier_bid_analysis") is True
        assert result.is_enabled("ai_assisted_tco_analysis") is False

    def test_get_feature_statuses_sends_only_app_tenant_id(self):
        client, mock_http = _make_client(app_tenant_id=_app_tid("tenant-9"))
        mock_http.request.return_value = _mock_response(json_body={"features": []})
        client.get_feature_statuses()
        called_url = mock_http.request.call_args.kwargs["url"]
        assert called_url.endswith("/feature/v1/features?appTenantId=tenant-9")

    def test_get_feature_statuses_on_404_raises_cbc_client_error(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            status_code=404,
            content=b'{"error":{"code":"NOT_FOUND","message":"not found"}}',
        )
        with pytest.raises(CBCClientError):
            client.get_feature_statuses()

    def test_get_feature_statuses_on_500_raises_cbc_server_error(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(status_code=500, content=b"")
        with pytest.raises(CBCServerError):
            client.get_feature_statuses()

    def test_get_feature_statuses_on_connection_failure_raises_cbc_network_error(self):
        client, mock_http = _make_client()
        mock_http.request.side_effect = httpx.ConnectError("refused")
        with pytest.raises(CBCNetworkError):
            client.get_feature_statuses()


# ---------------------------------------------------------------------------
# CBCClient — get_feature_status
# ---------------------------------------------------------------------------


class TestGetFeatureStatus:
    def test_get_feature_status_returns_matching_feature(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
                "features": [
                    {"featureId": "ai_assisted_supplier_bid_analysis", "enabled": True}
                ]
            }
        )
        result = client.get_feature_status("ai_assisted_supplier_bid_analysis")
        assert result is not None
        assert result.feature_id == "ai_assisted_supplier_bid_analysis"
        assert result.enabled is True

    def test_get_feature_status_sends_both_query_params(self):
        client, mock_http = _make_client(app_tenant_id=_app_tid("tenant-9"))
        mock_http.request.return_value = _mock_response(json_body={"features": []})
        client.get_feature_status("ai_assisted_lead_routing")
        called_url = mock_http.request.call_args.kwargs["url"]
        assert called_url.endswith(
            "/feature/v1/features"
            "?appTenantId=tenant-9&featureId=ai_assisted_lead_routing"
        )

    def test_get_feature_status_returns_none_when_feature_absent(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(json_body={"features": []})
        assert client.get_feature_status("ai_assisted_lead_routing") is None

    def test_get_feature_status_filters_to_requested_feature_from_full_list(self):
        # If the server ignores featureId and returns all features, the client
        # still extracts the requested one.
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(
            json_body={
                "features": [
                    {"featureId": "ai_assisted_supplier_bid_analysis", "enabled": True},
                    {"featureId": "ai_assisted_tco_analysis", "enabled": False},
                ]
            }
        )
        result = client.get_feature_status("ai_assisted_tco_analysis")
        assert result is not None
        assert result.feature_id == "ai_assisted_tco_analysis"
        assert result.enabled is False


# ---------------------------------------------------------------------------
# CBCClient — context manager
# ---------------------------------------------------------------------------


class TestCBCClientContextManager:
    def test_context_manager_on_exit_closes_http_client(self):
        client, mock_http = _make_client()
        with client:
            pass
        mock_http.close.assert_called_once()


# ---------------------------------------------------------------------------
# create_client — override path (CBCConfig axes)
# ---------------------------------------------------------------------------


class TestCreateClient:
    def test_create_client_with_base_url_and_app_tenant_id_overrides_returns_client(
        self,
    ):
        client = create_client(
            CBCConfig(
                base_url="http://localhost:8001",
                app_tenant_id="app-t1",
            )
        )
        assert isinstance(client, CBCClient)
        # String overrides are wrapped into callables and resolved per request.
        assert client._base_url() == "http://localhost:8001"
        assert client._resolve_app_tenant_id() == "app-t1"

    def test_create_client_with_callable_overrides_are_invoked_per_request(self):
        client = create_client(
            CBCConfig(
                base_url=lambda: "https://cbc.example.ondemand.com",
                app_tenant_id=lambda: "app-t1",
            )
        )
        assert isinstance(client, CBCClient)
        assert client._base_url() == "https://cbc.example.ondemand.com"
        assert client._resolve_app_tenant_id() == "app-t1"

    def test_create_client_with_ssl_context_override_passes_it_through(self):
        ctx = ssl.create_default_context()
        client = create_client(
            CBCConfig(
                base_url="https://cbc.example.ondemand.com",
                app_tenant_id="app-t1",
                ssl_context=lambda: ctx,
            )
        )
        assert isinstance(client, CBCClient)
        factory = client._ssl_factory
        assert factory is not None
        assert factory() is ctx


# ---------------------------------------------------------------------------
# _is_tls_failure
# ---------------------------------------------------------------------------


def _tls_read_error() -> httpx.ReadError:
    """A ReadError wrapping an ssl.SSLError, as httpx surfaces an expired cert.

    Mirrors the empirically-observed shape: httpx.ReadError whose cause chain
    reaches an ssl.SSLError (SSLV3_ALERT_CERTIFICATE_EXPIRED) a couple of levels
    down.
    """
    ssl_err = ssl.SSLError("[SSL: SSLV3_ALERT_CERTIFICATE_EXPIRED] certificate expired")
    read_err = httpx.ReadError("TLS handshake failed")
    read_err.__cause__ = ssl_err
    return read_err


class TestIsTlsFailure:
    def test_is_tls_failure_with_read_error_wrapping_ssl_error_returns_true(self):
        assert _is_tls_failure(_tls_read_error()) is True

    def test_is_tls_failure_with_connect_error_returns_false(self):
        assert _is_tls_failure(httpx.ConnectError("connection refused")) is False

    def test_is_tls_failure_with_non_ssl_os_error_returns_false(self):
        err = httpx.ReadError("read failed")
        err.__cause__ = OSError("broken pipe")
        assert _is_tls_failure(err) is False


# ---------------------------------------------------------------------------
# CBCClient — mTLS certificate rotation (reactive rebuild)
# ---------------------------------------------------------------------------


class TestCertRotation:
    def _rotating_client(
        self, factory: Callable[[], ssl.SSLContext]
    ) -> tuple[CBCClient, list[MagicMock]]:
        """A CBCClient whose _build_http_client hands out fresh mock http clients.

        Each rebuild appends a new mock to the returned list, so a test can
        assert how many times (and with what behaviour) the client was rebuilt.
        The provided ``factory`` is wired as ``ssl_context`` so its invocation
        count reflects each reactive rebuild (the initial mock below is injected
        directly, bypassing the factory, as the real ``http_client`` seam does).
        """
        built: list[MagicMock] = []

        def build() -> httpx.Client:
            factory()  # exercise the ssl factory, same as the real _build_http_client
            mock = MagicMock(spec=httpx.Client)
            built.append(mock)
            return mock

        initial = MagicMock(spec=httpx.Client)
        built.append(initial)
        client = CBCClient(
            base_url=lambda: "https://cbc.example.ondemand.com",
            app_tenant_id=_app_tid(),
            http_client=initial,
            ssl_context=factory,
        )
        client._build_http_client = build  # ty: ignore[invalid-assignment]
        return client, built

    def test_cert_rotation_on_tls_failure_rebuilds_client_and_retries_successfully(
        self,
    ):
        calls = {"factory": 0}

        def factory() -> ssl.SSLContext:
            calls["factory"] += 1
            return ssl.create_default_context()

        client, built = self._rotating_client(factory)
        ok = _mock_response(json_body={"items": [{"version": "cv1"}]})
        built[0].request.side_effect = _tls_read_error()
        # the rebuilt client answers ok; wire it the moment it is created
        orig_build = client._build_http_client

        def build_then_prime() -> httpx.Client:
            mock = cast(MagicMock, orig_build())
            mock.request.return_value = ok
            return mock

        client._build_http_client = build_then_prime  # ty: ignore[invalid-assignment]

        result = client.get_consumption_versions()

        assert len(built) == 2  # initial + one rebuild
        assert calls["factory"] == 1  # factory invoked once, on the rebuild
        built[1].request.assert_called_once()
        assert result.items[0].version == "cv1"

    def test_cert_rotation_on_second_tls_failure_after_rebuild_propagates_error(self):
        def factory() -> ssl.SSLContext:
            return ssl.create_default_context()

        client, built = self._rotating_client(factory)
        built[0].request.side_effect = _tls_read_error()
        orig_build = client._build_http_client

        def build_then_fail() -> httpx.Client:
            mock = cast(MagicMock, orig_build())
            mock.request.side_effect = _tls_read_error()
            return mock

        client._build_http_client = build_then_fail  # ty: ignore[invalid-assignment]

        with pytest.raises(CBCNetworkError):
            client.get_consumption_versions()

        # exactly one rebuild → built[0] + built[1]; no third client
        assert len(built) == 2
        built[1].request.assert_called_once()

    def test_cert_rotation_on_non_tls_transport_error_does_not_rebuild_client(self):
        def factory() -> ssl.SSLContext:
            return ssl.create_default_context()

        client, built = self._rotating_client(factory)
        built[0].request.side_effect = httpx.ConnectError("connection refused")

        with pytest.raises(CBCNetworkError):
            client.get_consumption_versions()

        # no rebuild — still only the initial mock
        assert len(built) == 1

    def test_cert_rotation_without_ssl_factory_does_not_rebuild_client(self):
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.request.side_effect = _tls_read_error()
        client = CBCClient(
            base_url=lambda: "https://cbc.example.ondemand.com",
            app_tenant_id=_app_tid(),
            http_client=mock_http,
            ssl_context=None,
        )
        with pytest.raises(CBCNetworkError):
            client.get_consumption_versions()
        # one attempt only, no rebuild path
        mock_http.request.assert_called_once()

    def test_cert_rotation_when_factory_fails_propagates_error_and_retains_old_client(
        self,
    ):
        calls = {"factory": 0}

        def factory() -> ssl.SSLContext:
            calls["factory"] += 1
            # The initial client is injected via http_client (factory not called
            # at construction), so the first invocation is the reactive rebuild —
            # which fails, as a rotated-but-unfetchable cert would.
            raise CBCConfigError("could not fetch the mTLS certificate")

        mock_http = MagicMock(spec=httpx.Client)
        mock_http.request.side_effect = _tls_read_error()
        client = CBCClient(
            base_url=lambda: "https://cbc.example.ondemand.com",
            app_tenant_id=_app_tid(),
            http_client=mock_http,
            ssl_context=factory,
        )
        original = client._http_client

        with pytest.raises(CBCConfigError, match="mTLS certificate"):
            client.get_consumption_versions()

        # factory invoked once on the failed rebuild; client left on the prior one
        assert calls["factory"] == 1
        assert client._http_client is original
        mock_http.request.assert_called_once()
