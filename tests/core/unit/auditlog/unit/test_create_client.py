"""Tests for client factory function."""

import pytest
from unittest.mock import patch, MagicMock

from sap_cloud_sdk.core.auditlog import create_client, AuditLogClient
from sap_cloud_sdk.core.auditlog._http_transport import HttpTransport
from sap_cloud_sdk.core.auditlog.config import AuditLogConfig
from sap_cloud_sdk.core.auditlog.exceptions import ClientCreationError


class TestCreateClient:

    @patch('sap_cloud_sdk.core.auditlog._load_config_from_env')
    @patch('sap_cloud_sdk.core.auditlog.HttpTransport')
    def test_create_client_cloud_mode(self, mock_http_transport, mock_load_config):
        mock_config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )
        mock_load_config.return_value = mock_config
        
        mock_transport = MagicMock()
        mock_http_transport.return_value = mock_transport
        
        client = create_client()
        
        assert isinstance(client, AuditLogClient)
        mock_load_config.assert_called_once()
        mock_http_transport.assert_called_once_with(mock_config)
        assert client._transport == mock_transport

    @patch('sap_cloud_sdk.core.auditlog.HttpTransport')
    def test_create_client_with_custom_config(self, mock_http_transport):
        custom_config = AuditLogConfig(
            client_id="custom_client",
            client_secret="custom_secret",
            oauth_url="https://custom-oauth.example.com",
            service_url="https://custom-service.example.com"
        )
        
        mock_transport = MagicMock()
        mock_http_transport.return_value = mock_transport
        
        client = create_client(config=custom_config)
        
        assert isinstance(client, AuditLogClient)
        mock_http_transport.assert_called_once_with(custom_config)
        assert client._transport == mock_transport

    @patch('sap_cloud_sdk.core.auditlog._load_config_from_env')
    def test_create_client_config_loading_exception(self, mock_load_config):
        mock_load_config.side_effect = Exception("Config loading failed")
        
        with pytest.raises(ClientCreationError, match="Failed to create audit log client"):
            create_client()

    @patch('sap_cloud_sdk.core.auditlog._load_config_from_env')
    @patch('sap_cloud_sdk.core.auditlog.HttpTransport')
    def test_create_client_http_transport_exception(self, mock_http_transport, mock_load_config):
        mock_config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )
        mock_load_config.return_value = mock_config
        
        mock_http_transport.side_effect = Exception("HTTP transport failed")
        
        with pytest.raises(ClientCreationError, match="Failed to create audit log client"):
            create_client()

    @patch('sap_cloud_sdk.core.auditlog.HttpTransport')
    def test_create_client_custom_config_transport_exception(self, mock_http_transport):
        custom_config = AuditLogConfig(
            client_id="custom_client",
            client_secret="custom_secret",
            oauth_url="https://custom-oauth.example.com",
            service_url="https://custom-service.example.com"
        )
        
        mock_http_transport.side_effect = Exception("Custom transport failed")
        
        with pytest.raises(ClientCreationError, match="Failed to create audit log client"):
            create_client(config=custom_config)

    @patch('sap_cloud_sdk.core.auditlog._load_config_from_env')
    @patch('sap_cloud_sdk.core.auditlog.HttpTransport')
    @patch('sap_cloud_sdk.core.auditlog.AuditLogClient')
    def test_create_client_client_creation_exception(self, mock_client_class, mock_http_transport, mock_load_config):
        mock_config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )
        mock_load_config.return_value = mock_config
        
        mock_transport = MagicMock()
        mock_http_transport.return_value = mock_transport
        
        mock_client_class.side_effect = Exception("Client creation failed")
        
        with pytest.raises(ClientCreationError, match="Failed to create audit log client"):
            create_client()

    def test_create_client_keyword_only_parameter(self):
        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )
        
        with patch('sap_cloud_sdk.core.auditlog.HttpTransport'):
            with pytest.raises(TypeError):
                create_client(config)  # ty: ignore[too-many-positional-arguments]
