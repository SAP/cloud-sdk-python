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

_NO_MOCK_FILE = patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: False)


class TestCreateClient:
    """Tests for create_client cloud mode."""

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_client_with_explicit_config(self, mock_http, mock_token_provider):
        config = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
            identityzone="provider-zone"
        )
        mock_token_provider.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_client(config=config)
        assert isinstance(client, DestinationClient)
        mock_token_provider.assert_called_once_with(config)
        mock_http.assert_called_once_with(config=config, token_provider=mock_token_provider.return_value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_client_cloud_mode_default(self, mock_http, mock_token_provider, mock_load_config):
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_token_provider.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_client()
        assert isinstance(client, DestinationClient)
        mock_load_config.assert_called_once_with(None)
        mock_token_provider.assert_called_once_with(mock_config)
        mock_http.assert_called_once_with(config=mock_config, token_provider=mock_token_provider.return_value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_client_cloud_mode_with_instance_name(self, mock_http, mock_token_provider, mock_load_config):
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_token_provider.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_client(instance="custom-instance")
        assert isinstance(client, DestinationClient)
        mock_load_config.assert_called_once_with("custom-instance")

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    def test_create_client_config_error(self, mock_load_config):
        mock_load_config.side_effect = Exception("Config loading failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_client()
        assert "failed to create destination client" in str(exc_info.value)
        assert "Config loading failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    def test_create_client_token_provider_error(self, mock_token_provider, mock_load_config):
        mock_load_config.return_value = Mock(spec=DestinationConfig)
        mock_token_provider.side_effect = Exception("Token provider failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_client()
        assert "failed to create destination client" in str(exc_info.value)
        assert "Token provider failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_client_http_error(self, mock_http, mock_token_provider, mock_load_config):
        mock_load_config.return_value = Mock(spec=DestinationConfig)
        mock_token_provider.return_value = Mock()
        mock_http.side_effect = Exception("HTTP client failed")
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

    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: False)
    def test_falls_through_to_cloud_when_no_mock_file(self, mock_load_config, mock_http, mock_tp):
        mock_load_config.return_value = Mock(spec=DestinationConfig)
        mock_tp.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_client()
        assert isinstance(client, DestinationClient)


class TestCreateFragmentClient:
    """Tests for create_fragment_client cloud mode."""

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_fragment_client_default(self, mock_http, mock_token_provider, mock_load_config):
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_token_provider.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_fragment_client()
        assert isinstance(client, FragmentClient)
        mock_load_config.assert_called_once_with(None)
        mock_token_provider.assert_called_once_with(mock_config)
        mock_http.assert_called_once_with(config=mock_config, token_provider=mock_token_provider.return_value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_fragment_client_with_explicit_config(self, mock_http, mock_token_provider):
        config = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
            identityzone="provider-zone"
        )
        mock_token_provider.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_fragment_client(config=config)
        assert isinstance(client, FragmentClient)
        mock_token_provider.assert_called_once_with(config)
        mock_http.assert_called_once_with(config=config, token_provider=mock_token_provider.return_value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_fragment_client_with_instance_name(self, mock_http, mock_token_provider, mock_load_config):
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_token_provider.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_fragment_client(instance="custom-instance")
        assert isinstance(client, FragmentClient)
        mock_load_config.assert_called_once_with("custom-instance")

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    def test_create_fragment_client_config_error(self, mock_load_config):
        mock_load_config.side_effect = Exception("Config loading failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_fragment_client()
        assert "failed to create fragment client" in str(exc_info.value)
        assert "Config loading failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    def test_create_fragment_client_token_provider_error(self, mock_token_provider, mock_load_config):
        mock_load_config.return_value = Mock(spec=DestinationConfig)
        mock_token_provider.side_effect = Exception("Token provider failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_fragment_client()
        assert "failed to create fragment client" in str(exc_info.value)
        assert "Token provider failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_fragment_client_http_error(self, mock_http, mock_token_provider, mock_load_config):
        mock_load_config.return_value = Mock(spec=DestinationConfig)
        mock_token_provider.return_value = Mock()
        mock_http.side_effect = Exception("HTTP client failed")
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

    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: False)
    def test_falls_through_to_cloud_when_no_mock_file(self, mock_load_config, mock_http, mock_tp):
        mock_load_config.return_value = Mock(spec=DestinationConfig)
        mock_tp.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_fragment_client()
        assert isinstance(client, FragmentClient)


class TestCreateCertificateClient:
    """Tests for create_certificate_client cloud mode."""

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_certificate_client_with_explicit_config(self, mock_http, mock_token_provider):
        config = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
            identityzone="provider-zone"
        )
        mock_token_provider.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_certificate_client(config=config)
        assert isinstance(client, CertificateClient)
        mock_token_provider.assert_called_once_with(config)
        mock_http.assert_called_once_with(config=config, token_provider=mock_token_provider.return_value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_certificate_client_cloud_mode_default(self, mock_http, mock_token_provider, mock_load_config):
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_token_provider.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_certificate_client()
        assert isinstance(client, CertificateClient)
        mock_load_config.assert_called_once_with(None)
        mock_token_provider.assert_called_once_with(mock_config)
        mock_http.assert_called_once_with(config=mock_config, token_provider=mock_token_provider.return_value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_certificate_client_cloud_mode_with_instance_name(self, mock_http, mock_token_provider, mock_load_config):
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_token_provider.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_certificate_client(instance="custom-instance")
        assert isinstance(client, CertificateClient)
        mock_load_config.assert_called_once_with("custom-instance")

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    def test_create_certificate_client_config_error(self, mock_load_config):
        mock_load_config.side_effect = Exception("Config loading failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_certificate_client()
        assert "failed to create certificate client" in str(exc_info.value)
        assert "Config loading failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    def test_create_certificate_client_token_provider_error(self, mock_token_provider, mock_load_config):
        mock_load_config.return_value = Mock(spec=DestinationConfig)
        mock_token_provider.side_effect = Exception("Token provider failed")
        with pytest.raises(ClientCreationError) as exc_info:
            create_certificate_client()
        assert "failed to create certificate client" in str(exc_info.value)
        assert "Token provider failed" in str(exc_info.value)

    @_NO_MOCK_FILE
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    def test_create_certificate_client_http_error(self, mock_http, mock_token_provider, mock_load_config):
        mock_load_config.return_value = Mock(spec=DestinationConfig)
        mock_token_provider.return_value = Mock()
        mock_http.side_effect = Exception("HTTP client failed")
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

    @patch("sap_cloud_sdk.destination.TokenProvider")
    @patch("sap_cloud_sdk.destination.DestinationHttp")
    @patch("sap_cloud_sdk.destination.load_from_env_or_mount")
    @patch("sap_cloud_sdk.destination.os.path.isfile", new=lambda _: False)
    def test_falls_through_to_cloud_when_no_mock_file(self, mock_load_config, mock_http, mock_tp):
        mock_load_config.return_value = Mock(spec=DestinationConfig)
        mock_tp.return_value = Mock()
        mock_http.return_value = Mock()
        client = create_certificate_client()
        assert isinstance(client, CertificateClient)
