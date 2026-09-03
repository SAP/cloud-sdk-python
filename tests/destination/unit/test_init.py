"""Unit tests for factory functions in __init__.py."""

import pytest
from unittest.mock import Mock, patch

from sap_cloud_sdk.destination._local_client_base import (
    DESTINATION_MOCK_FILE,
    FRAGMENT_MOCK_FILE,
    CERTIFICATE_MOCK_FILE,
)
from sap_cloud_sdk.destination import create_client, create_fragment_client, create_certificate_client
from sap_cloud_sdk.destination.client import DestinationClient
from sap_cloud_sdk.destination.fragment_client import FragmentClient
from sap_cloud_sdk.destination.certificate_client import CertificateClient
from sap_cloud_sdk.destination.local_client import LocalDevDestinationClient
from sap_cloud_sdk.destination.local_fragment_client import LocalDevFragmentClient
from sap_cloud_sdk.destination.local_certificate_client import LocalDevCertificateClient
from sap_cloud_sdk.destination.config import DestinationConfig
from sap_cloud_sdk.destination.exceptions import ClientCreationError
from sap_cloud_sdk.core.telemetry import Module

_NO_MOCK_FILE = patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: False)
_BUILD_HTTP = "sap_cloud_sdk.destination._build_destination_http"


class TestCreateClient:
    """Tests for create_client cloud mode."""

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_client_with_explicit_config(self, mock_build_http):
        config = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
            identityzone="provider-zone"
        )
        mock_build_http.return_value = Mock()
        client = create_client(config=config)
        assert isinstance(client, DestinationClient)
        mock_build_http.assert_called_once_with(None, config)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_client_cloud_mode_default(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_client()
        assert isinstance(client, DestinationClient)
        mock_build_http.assert_called_once_with(None, None)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_client_cloud_mode_with_instance_name(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_client(instance="custom-instance")
        assert isinstance(client, DestinationClient)
        mock_build_http.assert_called_once_with("custom-instance", None)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_client_config_error(self, mock_build_http):
        mock_build_http.side_effect = Exception("Config loading failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_client()
        assert "failed to create destination client" in str(exc_info.value)
        assert "Config loading failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_client_token_provider_error(self, mock_build_http):
        mock_build_http.side_effect = Exception("Token provider failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_client()
        assert "failed to create destination client" in str(exc_info.value)
        assert "Token provider failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_client_http_error(self, mock_build_http):
        mock_build_http.side_effect = Exception("HTTP client failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_client()
        assert "failed to create destination client" in str(exc_info.value)
        assert "HTTP client failed" in str(exc_info.value)


class TestCreateClientLocalMode:
    """Tests for create_client local mock mode detection."""

    @patch("sap_cloud_sdk.destination._local_client_base.os.path.abspath")
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: True)
    def test_returns_local_client_when_mock_file_exists(self, mock_abspath, tmp_path):
        mock_abspath.return_value = str(tmp_path)
        client = create_client()
        assert isinstance(client, LocalDevDestinationClient)

    @patch("sap_cloud_sdk.destination._local_client_base.os.path.abspath")
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: True)
    def test_logs_warning_in_local_mode(self, mock_abspath, tmp_path):
        mock_abspath.return_value = str(tmp_path)
        with patch("sap_cloud_sdk.destination.logger") as mock_logger:
            create_client()
        mock_logger.warning.assert_called_once()
        assert "local" in mock_logger.warning.call_args[0][0].lower()
        assert "production" in mock_logger.warning.call_args[0][0].lower()

    @patch(_BUILD_HTTP)
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: False)
    def test_falls_through_to_cloud_when_no_mock_file(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_client()
        assert isinstance(client, DestinationClient)


class TestCreateFragmentClient:
    """Tests for create_fragment_client cloud mode."""

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_fragment_client_default(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_fragment_client()
        assert isinstance(client, FragmentClient)
        mock_build_http.assert_called_once_with(None, None)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_fragment_client_with_explicit_config(self, mock_build_http):
        config = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
            identityzone="provider-zone"
        )
        mock_build_http.return_value = Mock()
        client = create_fragment_client(config=config)
        assert isinstance(client, FragmentClient)
        mock_build_http.assert_called_once_with(None, config)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_fragment_client_with_instance_name(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_fragment_client(instance="custom-instance")
        assert isinstance(client, FragmentClient)
        mock_build_http.assert_called_once_with("custom-instance", None)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_fragment_client_config_error(self, mock_build_http):
        mock_build_http.side_effect = Exception("Config loading failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_fragment_client()
        assert "failed to create fragment client" in str(exc_info.value)
        assert "Config loading failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_fragment_client_token_provider_error(self, mock_build_http):
        mock_build_http.side_effect = Exception("Token provider failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_fragment_client()
        assert "failed to create fragment client" in str(exc_info.value)
        assert "Token provider failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_fragment_client_http_error(self, mock_build_http):
        mock_build_http.side_effect = Exception("HTTP client failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_fragment_client()
        assert "failed to create fragment client" in str(exc_info.value)
        assert "HTTP client failed" in str(exc_info.value)


class TestCreateFragmentClientLocalMode:
    """Tests for create_fragment_client local mock mode detection."""

    @patch("sap_cloud_sdk.destination._local_client_base.os.path.abspath")
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: True)
    def test_returns_local_client_when_mock_file_exists(self, mock_abspath, tmp_path):
        mock_abspath.return_value = str(tmp_path)
        client = create_fragment_client()
        assert isinstance(client, LocalDevFragmentClient)

    @patch("sap_cloud_sdk.destination._local_client_base.os.path.abspath")
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: True)
    def test_logs_warning_in_local_mode(self, mock_abspath, tmp_path):
        mock_abspath.return_value = str(tmp_path)
        with patch("sap_cloud_sdk.destination.logger") as mock_logger:
            create_fragment_client()
        mock_logger.warning.assert_called_once()
        assert "local" in mock_logger.warning.call_args[0][0].lower()
        assert "production" in mock_logger.warning.call_args[0][0].lower()

    @patch(_BUILD_HTTP)
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: False)
    def test_falls_through_to_cloud_when_no_mock_file(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_fragment_client()
        assert isinstance(client, FragmentClient)


class TestCreateCertificateClient:
    """Tests for create_certificate_client cloud mode."""

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_certificate_client_with_explicit_config(self, mock_build_http):
        config = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
            identityzone="provider-zone"
        )
        mock_build_http.return_value = Mock()
        client = create_certificate_client(config=config)
        assert isinstance(client, CertificateClient)
        mock_build_http.assert_called_once_with(None, config)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_certificate_client_cloud_mode_default(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_certificate_client()
        assert isinstance(client, CertificateClient)
        mock_build_http.assert_called_once_with(None, None)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_certificate_client_cloud_mode_with_instance_name(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_certificate_client(instance="custom-instance")
        assert isinstance(client, CertificateClient)
        mock_build_http.assert_called_once_with("custom-instance", None)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_certificate_client_config_error(self, mock_build_http):
        mock_build_http.side_effect = Exception("Config loading failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_certificate_client()
        assert "failed to create certificate client" in str(exc_info.value)
        assert "Config loading failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_certificate_client_token_provider_error(self, mock_build_http):
        mock_build_http.side_effect = Exception("Token provider failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_certificate_client()
        assert "failed to create certificate client" in str(exc_info.value)
        assert "Token provider failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_create_certificate_client_http_error(self, mock_build_http):
        mock_build_http.side_effect = Exception("HTTP client failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_certificate_client()
        assert "failed to create certificate client" in str(exc_info.value)
        assert "HTTP client failed" in str(exc_info.value)


class TestCreateCertificateClientLocalMode:
    """Tests for create_certificate_client local mock mode detection."""

    @patch("sap_cloud_sdk.destination._local_client_base.os.path.abspath")
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: True)
    def test_returns_local_client_when_mock_file_exists(self, mock_abspath, tmp_path):
        mock_abspath.return_value = str(tmp_path)
        client = create_certificate_client()
        assert isinstance(client, LocalDevCertificateClient)

    @patch("sap_cloud_sdk.destination._local_client_base.os.path.abspath")
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: True)
    def test_logs_warning_in_local_mode(self, mock_abspath, tmp_path):
        mock_abspath.return_value = str(tmp_path)
        with patch("sap_cloud_sdk.destination.logger") as mock_logger:
            create_certificate_client()
        mock_logger.warning.assert_called_once()
        assert "local" in mock_logger.warning.call_args[0][0].lower()
        assert "production" in mock_logger.warning.call_args[0][0].lower()

    @patch(_BUILD_HTTP)
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: False)
    def test_falls_through_to_cloud_when_no_mock_file(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_certificate_client()
        assert isinstance(client, CertificateClient)


class TestCreateClientTelemetrySource:
    """Verify _telemetry_source kwarg is stored on the client."""

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_default_source_is_none(self, mock_build_http):
        mock_build_http.return_value = Mock()
        assert create_client()._telemetry_source is None

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_explicit_source_is_stored(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_client(_telemetry_source=Module.AGENTGATEWAY)
        assert client._telemetry_source is Module.AGENTGATEWAY


class TestCreateFragmentClientTelemetrySource:
    """Verify _telemetry_source kwarg is stored on the fragment client."""

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_default_source_is_none(self, mock_build_http):
        mock_build_http.return_value = Mock()
        assert create_fragment_client()._telemetry_source is None

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_explicit_source_is_stored(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_fragment_client(_telemetry_source=Module.AGENTGATEWAY)
        assert client._telemetry_source is Module.AGENTGATEWAY


class TestCreateCertificateClientTelemetrySource:
    """Verify _telemetry_source kwarg is stored on the certificate client."""

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_default_source_is_none(self, mock_build_http):
        mock_build_http.return_value = Mock()
        assert create_certificate_client()._telemetry_source is None

    @_NO_MOCK_FILE
    @patch(_BUILD_HTTP)
    def test_explicit_source_is_stored(self, mock_build_http):
        mock_build_http.return_value = Mock()
        client = create_certificate_client(_telemetry_source=Module.DATA_ANONYMIZATION)
        assert client._telemetry_source is Module.DATA_ANONYMIZATION
