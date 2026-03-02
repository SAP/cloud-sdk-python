"""Unit tests for factory functions in __init__.py."""

import pytest
from unittest.mock import Mock, patch

from cloud_sdk_python.destination import create_client, create_fragment_client, create_certificate_client
from cloud_sdk_python.destination.client import DestinationClient
from cloud_sdk_python.destination.fragment_client import FragmentClient
from cloud_sdk_python.destination.certificate_client import CertificateClient
from cloud_sdk_python.destination.config import DestinationConfig
from cloud_sdk_python.destination.exceptions import ClientCreationError


class TestCreateClient:
    """Tests for create_client factory function."""

    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_client_with_explicit_config(self, mock_http, mock_token_provider):
        """Test creating client with explicit configuration."""
        config = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
            identityzone="provider-zone"
        )
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http_instance = Mock()
        mock_http.return_value = mock_http_instance

        # Call function
        client = create_client(config=config)

        # Verify
        assert isinstance(client, DestinationClient)
        mock_token_provider.assert_called_once_with(config)
        mock_http.assert_called_once_with(config=config, token_provider=mock_tp)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_client_cloud_mode_default(self, mock_http, mock_token_provider, mock_load_config):
        """Test creating client in cloud mode with default configuration."""

        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http_instance = Mock()
        mock_http.return_value = mock_http_instance

        # Call function
        client = create_client()

        # Verify
        assert isinstance(client, DestinationClient)
        mock_load_config.assert_called_once_with(None)
        mock_token_provider.assert_called_once_with(mock_config)
        mock_http.assert_called_once_with(config=mock_config, token_provider=mock_tp)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_client_cloud_mode_with_instance_name(self, mock_http, mock_token_provider, mock_load_config):
        """Test creating client in cloud mode with custom instance name."""
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http_instance = Mock()
        mock_http.return_value = mock_http_instance

        # Call function
        client = create_client(instance="custom-instance")

        # Verify
        assert isinstance(client, DestinationClient)
        mock_load_config.assert_called_once_with("custom-instance")
        mock_token_provider.assert_called_once_with(mock_config)
        mock_http.assert_called_once_with(config=mock_config, token_provider=mock_tp)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    def test_create_client_config_error(self, mock_load_config):
        """Test that configuration errors are wrapped in ClientCreationError."""
        mock_load_config.side_effect = Exception("Config loading failed")

        # Call and verify
        with pytest.raises(ClientCreationError) as exc_info:
            create_client()

        assert "failed to create destination client" in str(exc_info.value)
        assert "Config loading failed" in str(exc_info.value)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    def test_create_client_token_provider_error(self, mock_token_provider, mock_load_config):
        """Test that token provider errors are wrapped in ClientCreationError."""
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_token_provider.side_effect = Exception("Token provider failed")

        # Call and verify
        with pytest.raises(ClientCreationError) as exc_info:
            create_client()

        assert "failed to create destination client" in str(exc_info.value)
        assert "Token provider failed" in str(exc_info.value)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_client_http_error(self, mock_http, mock_token_provider, mock_load_config):
        """Test that HTTP client errors are wrapped in ClientCreationError."""
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http.side_effect = Exception("HTTP client failed")

        # Call and verify
        with pytest.raises(ClientCreationError) as exc_info:
            create_client()

        assert "failed to create destination client" in str(exc_info.value)
        assert "HTTP client failed" in str(exc_info.value)


class TestCreateFragmentClient:
    """Tests for create_fragment_client factory function."""

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_fragment_client_default(self, mock_http, mock_token_provider, mock_load_config):
        """Test creating fragment client with default configuration."""
        # Setup mocks
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http_instance = Mock()
        mock_http.return_value = mock_http_instance

        # Call function
        client = create_fragment_client()

        # Verify
        assert isinstance(client, FragmentClient)
        mock_load_config.assert_called_once_with(None)
        mock_token_provider.assert_called_once_with(mock_config)
        mock_http.assert_called_once_with(config=mock_config, token_provider=mock_tp)

    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_fragment_client_with_explicit_config(self, mock_http, mock_token_provider):
        """Test creating fragment client with explicit configuration."""
        # Setup
        config = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
            identityzone="provider-zone"
        )
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http_instance = Mock()
        mock_http.return_value = mock_http_instance

        # Call function
        client = create_fragment_client(config=config)

        # Verify
        assert isinstance(client, FragmentClient)
        mock_token_provider.assert_called_once_with(config)
        mock_http.assert_called_once_with(config=config, token_provider=mock_tp)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_fragment_client_with_instance_name(self, mock_http, mock_token_provider, mock_load_config):
        """Test creating fragment client with custom instance name."""
        # Setup mocks
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http_instance = Mock()
        mock_http.return_value = mock_http_instance

        # Call function
        client = create_fragment_client(instance="custom-instance")

        # Verify
        assert isinstance(client, FragmentClient)
        mock_load_config.assert_called_once_with("custom-instance")
        mock_token_provider.assert_called_once_with(mock_config)
        mock_http.assert_called_once_with(config=mock_config, token_provider=mock_tp)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    def test_create_fragment_client_config_error(self, mock_load_config):
        """Test that configuration errors are wrapped in ClientCreationError."""
        # Setup
        mock_load_config.side_effect = Exception("Config loading failed")

        # Call and verify
        with pytest.raises(ClientCreationError) as exc_info:
            create_fragment_client()

        assert "failed to create fragment client" in str(exc_info.value)
        assert "Config loading failed" in str(exc_info.value)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    def test_create_fragment_client_token_provider_error(self, mock_token_provider, mock_load_config):
        """Test that token provider errors are wrapped in ClientCreationError."""
        # Setup
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_token_provider.side_effect = Exception("Token provider failed")

        # Call and verify
        with pytest.raises(ClientCreationError) as exc_info:
            create_fragment_client()

        assert "failed to create fragment client" in str(exc_info.value)
        assert "Token provider failed" in str(exc_info.value)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_fragment_client_http_error(self, mock_http, mock_token_provider, mock_load_config):
        """Test that HTTP client errors are wrapped in ClientCreationError."""
        # Setup
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http.side_effect = Exception("HTTP client failed")

        # Call and verify
        with pytest.raises(ClientCreationError) as exc_info:
            create_fragment_client()

        assert "failed to create fragment client" in str(exc_info.value)
        assert "HTTP client failed" in str(exc_info.value)


class TestCreateCertificateClient:
    """Tests for create_certificate_client factory function."""

    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_certificate_client_with_explicit_config(self, mock_http, mock_token_provider):
        """Test creating certificate client with explicit configuration."""

        config = DestinationConfig(
            url="https://destination.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
            identityzone="provider-zone"
        )
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http_instance = Mock()
        mock_http.return_value = mock_http_instance

        # Call function
        client = create_certificate_client(config=config)

        # Verify
        assert isinstance(client, CertificateClient)
        mock_token_provider.assert_called_once_with(config)
        mock_http.assert_called_once_with(config=config, token_provider=mock_tp)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_certificate_client_cloud_mode_default(self, mock_http, mock_token_provider, mock_load_config):
        """Test creating certificate client in cloud mode with default configuration."""
        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http_instance = Mock()
        mock_http.return_value = mock_http_instance

        # Call function
        client = create_certificate_client()

        # Verify
        assert isinstance(client, CertificateClient)
        mock_load_config.assert_called_once_with(None)
        mock_token_provider.assert_called_once_with(mock_config)
        mock_http.assert_called_once_with(config=mock_config, token_provider=mock_tp)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_certificate_client_cloud_mode_with_instance_name(self, mock_http, mock_token_provider, mock_load_config):
        """Test creating certificate client in cloud mode with custom instance name."""

        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http_instance = Mock()
        mock_http.return_value = mock_http_instance

        # Call function
        client = create_certificate_client(instance="custom-instance")

        # Verify
        assert isinstance(client, CertificateClient)
        mock_load_config.assert_called_once_with("custom-instance")
        mock_token_provider.assert_called_once_with(mock_config)
        mock_http.assert_called_once_with(config=mock_config, token_provider=mock_tp)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    def test_create_certificate_client_config_error(self, mock_load_config):
        """Test that configuration errors are wrapped in ClientCreationError."""

        mock_load_config.side_effect = Exception("Config loading failed")

        # Call and verify
        with pytest.raises(ClientCreationError) as exc_info:
            create_certificate_client()

        assert "failed to create certificate client" in str(exc_info.value)
        assert "Config loading failed" in str(exc_info.value)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    def test_create_certificate_client_token_provider_error(self, mock_token_provider, mock_load_config):
        """Test that token provider errors are wrapped in ClientCreationError."""

        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_token_provider.side_effect = Exception("Token provider failed")

        # Call and verify
        with pytest.raises(ClientCreationError) as exc_info:
            create_certificate_client()

        assert "failed to create certificate client" in str(exc_info.value)
        assert "Token provider failed" in str(exc_info.value)

    @patch("cloud_sdk_python.destination.load_from_env_or_mount")
    @patch("cloud_sdk_python.destination.TokenProvider")
    @patch("cloud_sdk_python.destination.DestinationHttp")
    def test_create_certificate_client_http_error(self, mock_http, mock_token_provider, mock_load_config):
        """Test that HTTP client errors are wrapped in ClientCreationError."""

        mock_config = Mock(spec=DestinationConfig)
        mock_load_config.return_value = mock_config
        mock_tp = Mock()
        mock_token_provider.return_value = mock_tp
        mock_http.side_effect = Exception("HTTP client failed")

        # Call and verify
        with pytest.raises(ClientCreationError) as exc_info:
            create_certificate_client()

        assert "failed to create certificate client" in str(exc_info.value)
        assert "HTTP client failed" in str(exc_info.value)
