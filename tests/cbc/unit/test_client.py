"""Unit tests for DefaultClient and create_client."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast
from unittest.mock import MagicMock

import httpx
import json
import pytest
import ssl

from sap_cloud_sdk.cbc.client import DefaultClient, create_client, _is_tls_failure
from sap_cloud_sdk.cbc.exceptions import (
    CBCClientError,
    CBCConfigError,
    CBCNetworkError,
    CBCServerError,
)
from sap_cloud_sdk.cbc._models import ConfigData, EntityData


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
# DefaultClient — get_entity_data
# ---------------------------------------------------------------------------


class TestGetEntityData:
    def test_returns_entity_data_directly(self):
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

    def test_uses_pinned_version_without_resolving(self):
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

    def test_raises_when_no_versions_exist(self):
        client, mock_http = _make_client()
        mock_http.request.return_value = _mock_response(json_body={"items": []})
        with pytest.raises(CBCClientError, match="no consumption version"):
            client.get_entity_data("payment-config", "payment-mode")


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
            ssl_context=lambda: ctx,
        )
        assert isinstance(client, DefaultClient)


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
    def test_true_for_read_error_wrapping_ssl_error(self):
        assert _is_tls_failure(_tls_read_error()) is True

    def test_false_for_plain_connect_error(self):
        assert _is_tls_failure(httpx.ConnectError("connection refused")) is False

    def test_false_for_non_ssl_os_error(self):
        err = httpx.ReadError("read failed")
        err.__cause__ = OSError("broken pipe")
        assert _is_tls_failure(err) is False


# ---------------------------------------------------------------------------
# DefaultClient — mTLS certificate rotation (reactive rebuild)
# ---------------------------------------------------------------------------


class TestCertRotation:
    def _rotating_client(
        self, factory: Callable[[], ssl.SSLContext]
    ) -> tuple[DefaultClient, list[MagicMock]]:
        """A DefaultClient whose _build_http_client hands out fresh mock http clients.

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
        client = DefaultClient(
            base_url=lambda: "https://cbc.example.ondemand.com",
            app_tenant_id=_app_tid(),
            http_client=initial,
            ssl_context=factory,
        )
        client._build_http_client = build  # ty: ignore[invalid-assignment]
        return client, built

    def test_reactive_success_rebuilds_and_retries(self):
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

    def test_second_failure_propagates_after_one_rebuild(self):
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

    def test_non_tls_transport_error_does_not_rebuild(self):
        def factory() -> ssl.SSLContext:
            return ssl.create_default_context()

        client, built = self._rotating_client(factory)
        built[0].request.side_effect = httpx.ConnectError("connection refused")

        with pytest.raises(CBCNetworkError):
            client.get_consumption_versions()

        # no rebuild — still only the initial mock
        assert len(built) == 1

    def test_no_factory_does_not_rebuild(self):
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.request.side_effect = _tls_read_error()
        client = DefaultClient(
            base_url=lambda: "https://cbc.example.ondemand.com",
            app_tenant_id=_app_tid(),
            http_client=mock_http,
            ssl_context=None,
        )
        with pytest.raises(CBCNetworkError):
            client.get_consumption_versions()
        # one attempt only, no rebuild path
        mock_http.request.assert_called_once()

    def test_rebuild_failure_propagates_and_keeps_client(self):
        calls = {"factory": 0}

        def factory() -> ssl.SSLContext:
            calls["factory"] += 1
            # The initial client is injected via http_client (factory not called
            # at construction), so the first invocation is the reactive rebuild —
            # which fails, as a rotated-but-unfetchable cert would.
            raise CBCConfigError("could not fetch the mTLS certificate")

        mock_http = MagicMock(spec=httpx.Client)
        mock_http.request.side_effect = _tls_read_error()
        client = DefaultClient(
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
