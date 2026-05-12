"""Tests for UMS transport setup, errors, tenant handling, and integration."""

import base64
import json
from unittest.mock import MagicMock, patch, ANY

import httpx
import pytest

from sap_cloud_sdk.extensibility._models import (
    ExtensionCapabilityImplementation,
)
from sap_cloud_sdk.extensibility._ums_transport import (
    UmsTransport,
    _ums_destination_name,
    _UMS_DESTINATION_PREFIX,
    ENV_CONHOS_LANDSCAPE,
    ENV_UMS_DESTINATION_NAME,
    _GRAPHQL_QUERY,
)
from sap_cloud_sdk.extensibility.config import ExtensibilityConfig
from sap_cloud_sdk.extensibility.exceptions import TransportError

from tests.extensibility.unit._ums_test_helpers import (
    AGENT_ORD_ID,
    _FAKE_PEM,
    _FAKE_PEM_B64,
    UMS_RESPONSE_SINGLE,
    UMS_RESPONSE_EMPTY,
    UMS_RESPONSE_DIFFERENT_CAPABILITY,
    _make_config,
    _make_dest,
    _make_httpx_response,
)


class TestUmsDestinationName:
    def test_constructs_from_landscape_env(self, monkeypatch):
        monkeypatch.delenv(ENV_UMS_DESTINATION_NAME, raising=False)
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")
        assert _ums_destination_name() == "sap-managed-runtime-ums-exttest-dev-eu12"

    def test_constructs_from_landscape_env_prod(self, monkeypatch):
        monkeypatch.delenv(ENV_UMS_DESTINATION_NAME, raising=False)
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "myagent-prod-eu10")
        assert _ums_destination_name() == "sap-managed-runtime-ums-myagent-prod-eu10"

    def test_returns_none_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv(ENV_UMS_DESTINATION_NAME, raising=False)
        monkeypatch.delenv(ENV_CONHOS_LANDSCAPE, raising=False)
        assert _ums_destination_name() is None

    def test_returns_none_when_env_empty(self, monkeypatch):
        monkeypatch.delenv(ENV_UMS_DESTINATION_NAME, raising=False)
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "")
        assert _ums_destination_name() is None

    def test_prefix_constant(self):
        assert _UMS_DESTINATION_PREFIX == "sap-managed-runtime-ums-"

    def test_override_env_takes_precedence(self, monkeypatch):
        monkeypatch.setenv(ENV_UMS_DESTINATION_NAME, "ums-exttest-dev-eu12")
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")
        assert _ums_destination_name() == "ums-exttest-dev-eu12"

    def test_override_env_without_landscape(self, monkeypatch):
        monkeypatch.setenv(ENV_UMS_DESTINATION_NAME, "my-custom-dest")
        monkeypatch.delenv(ENV_CONHOS_LANDSCAPE, raising=False)
        assert _ums_destination_name() == "my-custom-dest"

    def test_empty_override_falls_through_to_landscape(self, monkeypatch):
        monkeypatch.setenv(ENV_UMS_DESTINATION_NAME, "")
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")
        assert _ums_destination_name() == "sap-managed-runtime-ums-exttest-dev-eu12"

    def test_config_override_takes_highest_priority(self, monkeypatch):
        monkeypatch.setenv(ENV_UMS_DESTINATION_NAME, "env-override")
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")
        assert _ums_destination_name(config_override="config-dest") == "config-dest"

    def test_config_override_none_falls_through(self, monkeypatch):
        monkeypatch.setenv(ENV_UMS_DESTINATION_NAME, "env-override")
        assert _ums_destination_name(config_override=None) == "env-override"

    def test_config_override_empty_falls_through(self, monkeypatch):
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")
        monkeypatch.delenv(ENV_UMS_DESTINATION_NAME, raising=False)
        assert (
            _ums_destination_name(config_override="")
            == "sap-managed-runtime-ums-exttest-dev-eu12"
        )

# ---------------------------------------------------------------------------
# Tests: UmsTransport construction
# ---------------------------------------------------------------------------


class TestUmsTransportInit:
    @patch("sap_cloud_sdk.extensibility._ums_transport.create_destination_client")
    def test_valid_config(self, mock_dest_client, monkeypatch):
        monkeypatch.delenv(ENV_UMS_DESTINATION_NAME, raising=False)
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")
        config = _make_config()
        transport = UmsTransport(AGENT_ORD_ID, config)
        assert transport._config is config
        assert transport._destination_name == "sap-managed-runtime-ums-exttest-dev-eu12"
        mock_dest_client.assert_called_once_with(instance="default")

    @patch("sap_cloud_sdk.extensibility._ums_transport.create_destination_client")
    def test_destination_name_none_when_env_not_set(
        self, mock_dest_client, monkeypatch
    ):
        monkeypatch.delenv(ENV_UMS_DESTINATION_NAME, raising=False)
        monkeypatch.delenv(ENV_CONHOS_LANDSCAPE, raising=False)
        config = _make_config()
        transport = UmsTransport(AGENT_ORD_ID, config)
        assert transport._destination_name is None

    @patch("sap_cloud_sdk.extensibility._ums_transport.create_destination_client")
    def test_config_destination_name_override(self, mock_dest_client, monkeypatch):
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")
        config = _make_config(destination_name="MY_CUSTOM_DEST")
        transport = UmsTransport(AGENT_ORD_ID, config)
        assert transport._destination_name == "MY_CUSTOM_DEST"


# ---------------------------------------------------------------------------
# Tests: UmsTransport.get_extension_capability_implementation
# ---------------------------------------------------------------------------


class TestUmsTransportGetExtCapImpl:
    """Tests for the full transport flow."""

    @pytest.fixture(autouse=True)
    def _set_landscape_env(self, monkeypatch):
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")

    @patch("sap_cloud_sdk.extensibility._ums_transport.create_destination_client")
    def _make_transport(self, mock_dest_client, dest=None):
        config = _make_config()
        if dest is None:
            dest = _make_dest()
        mock_dest_client.return_value.get_destination.return_value = dest
        transport = UmsTransport(AGENT_ORD_ID, config)
        return transport, mock_dest_client.return_value

    @patch("sap_cloud_sdk.extensibility._ums_transport.create_destination_client")
    def test_raises_transport_error_when_destination_name_is_none(
        self, mock_dest_client, monkeypatch
    ):
        monkeypatch.delenv(ENV_CONHOS_LANDSCAPE, raising=False)
        monkeypatch.delenv(ENV_UMS_DESTINATION_NAME, raising=False)
        config = _make_config()
        transport = UmsTransport(AGENT_ORD_ID, config)
        assert transport._destination_name is None
        with pytest.raises(
            TransportError, match="UMS destination name could not be resolved"
        ):
            transport.get_extension_capability_implementation()

    def test_full_flow(self):
        transport, dest_client = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_SINGLE)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            result = transport.get_extension_capability_implementation()

        assert isinstance(result, ExtensionCapabilityImplementation)
        assert result.capability_id == "default"
        assert result.extension_names == ["ServiceNow Extension"]
        assert len(result.mcp_servers) == 1
        assert result.instruction == "Use ServiceNow tools for ticket management."

    def test_uses_resolved_destination_name(self):
        """Verify get_destination is called with the env-var-resolved name."""
        transport, dest_client = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_EMPTY)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            transport.get_extension_capability_implementation()

        dest_client.get_destination.assert_called_once_with(
            "sap-managed-runtime-ums-exttest-dev-eu12", level=ANY
        )

    def test_sends_correct_graphql_query(self):
        transport, dest_client = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_EMPTY)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            transport.get_extension_capability_implementation()

        # Verify the URL
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://ums.example.com/graphql"

        # Verify the GraphQL body
        json_body = call_args[1]["json"]
        assert json_body["query"] == _GRAPHQL_QUERY
        filters = json_body["variables"]["filters"]
        assert filters["agent"]["ordIdEquals"] == AGENT_ORD_ID
        assert "tenantInUMSIntersects" not in filters

    def test_client_cert_passed_to_httpx(self):
        transport, dest_client = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_EMPTY)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            transport.get_extension_capability_implementation()

        # httpx.Client constructed with cert= pointing to a temp file
        init_kwargs = mock_client_cls.call_args[1]
        assert "cert" in init_kwargs
        # The cert value should be a string (temp file path)
        assert isinstance(init_kwargs["cert"], str)
        assert init_kwargs["cert"].endswith(".pem")

    def test_custom_capability_id(self):
        transport, dest_client = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_DIFFERENT_CAPABILITY)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            result = transport.get_extension_capability_implementation(
                capability_id="onboarding"
            )

        assert result.capability_id == "onboarding"
        assert result.instruction == "Onboarding instruction."
        assert len(result.mcp_servers) == 1
        assert result.mcp_servers[0].ord_id == "sap.mcp:apiResource:onboarding:v1"

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_destination_resolution_failure(self):
        transport, dest_client = self._make_transport()
        dest_client.get_destination.side_effect = RuntimeError("no dest")

        with pytest.raises(TransportError, match="Failed to resolve destination"):
            transport.get_extension_capability_implementation()

    def test_destination_no_url(self):
        dest = _make_dest(url=None)
        transport, dest_client = self._make_transport(dest=dest)

        with pytest.raises(TransportError, match="has no URL configured"):
            transport.get_extension_capability_implementation()

    def test_http_request_failure(self):
        transport, dest_client = self._make_transport()

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("connection refused")

            with pytest.raises(
                TransportError, match="HTTP request to UMS endpoint failed"
            ):
                transport.get_extension_capability_implementation()

    def test_http_error_status(self):
        transport, dest_client = self._make_transport()
        response = _make_httpx_response({"error": "unauthorized"}, status_code=401)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            with pytest.raises(TransportError, match="UMS returned HTTP 401"):
                transport.get_extension_capability_implementation()

    def test_invalid_json_response(self):
        transport, dest_client = self._make_transport()
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.raise_for_status = MagicMock()
        response.json.side_effect = ValueError("invalid json")
        response.text = "not json"

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            with pytest.raises(
                TransportError, match="Failed to parse UMS response as JSON"
            ):
                transport.get_extension_capability_implementation()

    def test_graphql_errors(self):
        transport, dest_client = self._make_transport()
        gql_error_response = {
            "errors": [
                {"message": "Cannot query field 'x'"},
                {"message": "Another error"},
            ]
        }
        response = _make_httpx_response(gql_error_response)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            with pytest.raises(
                TransportError, match="UMS GraphQL errors.*Cannot query field"
            ):
                transport.get_extension_capability_implementation()

    def test_missing_data_field(self):
        transport, dest_client = self._make_transport()
        response = _make_httpx_response({"something_else": True})

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            with pytest.raises(TransportError, match="missing the 'data' field"):
                transport.get_extension_capability_implementation()

    def test_no_certificates_raises(self):
        dest = _make_dest(cert_content=None)
        transport, dest_client = self._make_transport(dest=dest)

        with pytest.raises(TransportError, match="has no client certificates"):
            transport.get_extension_capability_implementation()

    def test_invalid_cert_base64_raises(self):
        dest = _make_dest(cert_content="!!!not-valid-base64!!!")
        transport, dest_client = self._make_transport(dest=dest)

        with pytest.raises(TransportError, match="Failed to decode client certificate"):
            transport.get_extension_capability_implementation()

    def test_cert_content_written_to_temp_file(self):
        """Verify the decoded cert bytes are written to the temp file."""
        transport, dest_client = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_EMPTY)

        with (
            patch(
                "sap_cloud_sdk.extensibility._ums_transport.tempfile.NamedTemporaryFile"
            ) as mock_tmpfile,
            patch(
                "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
            ) as mock_client_cls,
        ):
            mock_file = MagicMock()
            mock_file.name = "/tmp/fake-cert.pem"
            mock_tmpfile.return_value.__enter__ = MagicMock(return_value=mock_file)
            mock_tmpfile.return_value.__exit__ = MagicMock(return_value=False)

            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            transport.get_extension_capability_implementation()

        # Verify decoded PEM bytes were written
        mock_file.write.assert_called_once_with(_FAKE_PEM)
        mock_file.flush.assert_called_once()

        # Verify httpx.Client received the temp file path
        init_kwargs = mock_client_cls.call_args[1]
        assert init_kwargs["cert"] == "/tmp/fake-cert.pem"

    def test_trailing_slash_on_url(self):
        """Base URL with trailing slash should not produce double slashes."""
        dest = _make_dest(url="https://ums.example.com/")
        transport, dest_client = self._make_transport(dest=dest)
        response = _make_httpx_response(UMS_RESPONSE_EMPTY)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            transport.get_extension_capability_implementation()

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://ums.example.com/graphql"


# ---------------------------------------------------------------------------
# Tests: UmsTransport tenant destination forwarding
# ---------------------------------------------------------------------------


class TestUmsTransportTenant:
    """Tests that tenant is used in the GraphQL filter and X-Tenant header."""

    @pytest.fixture(autouse=True)
    def _set_landscape_env(self, monkeypatch):
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")

    @patch("sap_cloud_sdk.extensibility._ums_transport.create_destination_client")
    def _make_transport(self, mock_dest_client, dest=None):
        config = _make_config()
        if dest is None:
            dest = _make_dest()
        mock_dest_client.return_value.get_destination.return_value = dest
        transport = UmsTransport(AGENT_ORD_ID, config)
        return transport, mock_dest_client.return_value

    def test_tenant_does_not_affect_destination_call(self):
        """Destination is always resolved provider-scoped, regardless of tenant."""
        transport, dest_client = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_EMPTY)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            transport.get_extension_capability_implementation(tenant="my-subscriber")

        # get_destination is called without any ConsumptionOptions
        dest_client.get_destination.assert_called_once_with(
            "sap-managed-runtime-ums-exttest-dev-eu12", level=ANY
        )

    def test_tenant_included_in_agent_filter(self):
        """Tenant is included as agent.uclSystemInstance.localTenantIdIn."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_EMPTY)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            transport.get_extension_capability_implementation(tenant="my-subscriber")

        json_body = mock_client.post.call_args[1]["json"]
        agent_filter = json_body["variables"]["filters"]["agent"]
        assert agent_filter["ordIdEquals"] == AGENT_ORD_ID
        assert agent_filter["uclSystemInstance"] == {
            "localTenantIdIn": "my-subscriber",
        }
        # tenantInUMSIntersects must NOT be present
        assert "tenantInUMSIntersects" not in json_body["variables"]["filters"]

    def test_x_tenant_header_set(self):
        """The X-Tenant HTTP header is set to the tenant value."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_EMPTY)

        with patch(
            "sap_cloud_sdk.extensibility._ums_transport.httpx.Client"
        ) as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = response

            transport.get_extension_capability_implementation(
                tenant="1d2e1a41-a28b-431f-9e3f-42e9704bfa75"
            )

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["X-Tenant"] == "1d2e1a41-a28b-431f-9e3f-42e9704bfa75"
        assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# Tests: create_client integration with UmsTransport
# ---------------------------------------------------------------------------


class TestCreateClientUmsIntegration:
    """Tests that create_client() correctly selects UmsTransport."""

    @patch("sap_cloud_sdk.extensibility.UmsTransport")
    def test_uses_ums_transport_with_config(self, mock_ums_cls):
        from sap_cloud_sdk.extensibility import create_client

        config = ExtensibilityConfig(destination_name="MY_UMS")
        client = create_client("sap.ai:agent:test:v1", config=config)

        mock_ums_cls.assert_called_once_with("sap.ai:agent:test:v1", config)
        assert client is not None

    @patch("sap_cloud_sdk.extensibility.UmsTransport")
    def test_ums_init_failure_degrades_to_noop(self, mock_ums_cls):
        from sap_cloud_sdk.extensibility import create_client
        from sap_cloud_sdk.extensibility.client import ExtensibilityClient

        mock_ums_cls.side_effect = RuntimeError("init failed")

        client = create_client("sap.ai:agent:test:v1")

        assert isinstance(client, ExtensibilityClient)
        # Should return empty results (NoOpTransport behavior)
        result = client.get_extension_capability_implementation(tenant="test-tenant")
        assert result.mcp_servers == []
        assert result.instruction is None
