"""Tests for HTTP transport implementation."""

import pytest
from unittest.mock import patch, MagicMock
import requests

from sap_cloud_sdk.auditlog._http_transport import HttpTransport
from sap_cloud_sdk.auditlog._transport import Transport
from sap_cloud_sdk.auditlog.config import AuditLogConfig
from sap_cloud_sdk.auditlog.models import (
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
    DataAccessAttribute
)
from sap_cloud_sdk.auditlog.exceptions import TransportError, AuthenticationError


class TestHttpTransport:

    def test_inherits_from_transport(self):
        assert issubclass(HttpTransport, Transport)

    @patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session')
    def test_initialization_success(self, mock_oauth_session):
        mock_session = MagicMock()
        mock_oauth_session.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "test_token"}

        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )

        transport = HttpTransport(config)

        assert transport.config == config
        mock_session.fetch_token.assert_called_once_with(
            token_url="https://oauth.example.com/oauth/token",
            client_id="test_client",
            client_secret="test_secret"
        )

    @patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session')
    def test_initialization_oauth_url_with_trailing_slash(self, mock_oauth_session):
        mock_session = MagicMock()
        mock_oauth_session.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "test_token"}

        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com/",
            service_url="https://service.example.com"
        )

        transport = HttpTransport(config)

        mock_session.fetch_token.assert_called_once_with(
            token_url="https://oauth.example.com/oauth/token",
            client_id="test_client",
            client_secret="test_secret"
        )

    @patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session')
    def test_initialization_auth_failure(self, mock_oauth_session):
        mock_session = MagicMock()
        mock_oauth_session.return_value = mock_session
        mock_session.fetch_token.side_effect = Exception("Auth failed")

        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )

        with pytest.raises(AuthenticationError, match="Failed to obtain OAuth2 token"):
            HttpTransport(config)

    def test_get_endpoint_security_event(self):
        with patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session') as mock_oauth:
            mock_session = MagicMock()
            mock_oauth.return_value = mock_session
            mock_session.fetch_token.return_value = {"access_token": "test_token"}

            config = AuditLogConfig(
                client_id="test_client",
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

            transport = HttpTransport(config)
            event = SecurityEvent(data="test")

            endpoint = transport._get_endpoint(event)
            assert endpoint == "/security-events"

    def test_get_endpoint_data_access_event(self):
        with patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session') as mock_oauth:
            mock_session = MagicMock()
            mock_oauth.return_value = mock_session
            mock_session.fetch_token.return_value = {"access_token": "test_token"}

            config = AuditLogConfig(
                client_id="test_client",
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

            transport = HttpTransport(config)
            event = DataAccessEvent(
                object_type="database",
                object_id={"table": "users"},
                subject_type="user",
                subject_id={"id": "123"},
                attributes=[DataAccessAttribute("email")]
            )

            endpoint = transport._get_endpoint(event)
            assert endpoint == "/data-accesses"

    def test_get_endpoint_data_modification_event(self):
        with patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session') as mock_oauth:
            mock_session = MagicMock()
            mock_oauth.return_value = mock_session
            mock_session.fetch_token.return_value = {"access_token": "test_token"}

            config = AuditLogConfig(
                client_id="test_client",
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

            transport = HttpTransport(config)
            event = DataModificationEvent(
                object_type="profile",
                object_id={"id": "123"},
                subject_type="user",
                subject_id={"id": "456"},
                attributes=[]
            )

            endpoint = transport._get_endpoint(event)
            assert endpoint == "/data-modifications"

    def test_get_endpoint_data_deletion_event(self):
        with patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session') as mock_oauth:
            mock_session = MagicMock()
            mock_oauth.return_value = mock_session
            mock_session.fetch_token.return_value = {"access_token": "test_token"}

            config = AuditLogConfig(
                client_id="test_client",
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

            transport = HttpTransport(config)
            event = DataDeletionEvent(
                object_type="profile",
                object_id={"id": "123"},
                subject_type="user",
                subject_id={"id": "456"},
                attributes=[]
            )

            endpoint = transport._get_endpoint(event)
            assert endpoint == "/data-modifications"

    def test_get_endpoint_configuration_change_event(self):
        with patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session') as mock_oauth:
            mock_session = MagicMock()
            mock_oauth.return_value = mock_session
            mock_session.fetch_token.return_value = {"access_token": "test_token"}

            config = AuditLogConfig(
                client_id="test_client",
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

            transport = HttpTransport(config)
            event = ConfigurationChangeEvent(
                object_type="config",
                object_id={"setting": "timeout"},
                attributes=[]
            )

            endpoint = transport._get_endpoint(event)
            assert endpoint == "/configuration-changes"

    def test_get_endpoint_configuration_deletion_event(self):
        with patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session') as mock_oauth:
            mock_session = MagicMock()
            mock_oauth.return_value = mock_session
            mock_session.fetch_token.return_value = {"access_token": "test_token"}

            config = AuditLogConfig(
                client_id="test_client",
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

            transport = HttpTransport(config)
            event = ConfigurationDeletionEvent(
                object_type="config",
                object_id={"setting": "timeout"},
                attributes=[]
            )

            endpoint = transport._get_endpoint(event)
            assert endpoint == "/configuration-changes"

    def test_get_endpoint_unknown_event(self):
        with patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session') as mock_oauth:
            mock_session = MagicMock()
            mock_oauth.return_value = mock_session
            mock_session.fetch_token.return_value = {"access_token": "test_token"}

            config = AuditLogConfig(
                client_id="test_client",
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

            transport = HttpTransport(config)

            class UnknownEvent:
                pass

            with pytest.raises(TransportError, match="Unknown event type"):
                transport._get_endpoint(UnknownEvent())  # ty: ignore[invalid-argument-type]

    @patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session')
    def test_send_success(self, mock_oauth_session):
        mock_session = MagicMock()
        mock_oauth_session.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "test_token"}

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.post.return_value = mock_response

        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )

        transport = HttpTransport(config)
        event = SecurityEvent(data="Test event")

        transport.send(event)

        mock_session.post.assert_called_once_with(
            "https://service.example.com/audit-log/oauth2/v2/security-events",
            json=event.to_dict(),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

    @patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session')
    def test_send_service_url_with_trailing_slash(self, mock_oauth_session):
        mock_session = MagicMock()
        mock_oauth_session.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "test_token"}

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.post.return_value = mock_response

        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com/"
        )

        transport = HttpTransport(config)
        event = SecurityEvent(data="Test event")

        transport.send(event)

        expected_url = "https://service.example.com/audit-log/oauth2/v2/security-events"
        mock_session.post.assert_called_once_with(
            expected_url,
            json=event.to_dict(),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

    @patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session')
    def test_send_http_error_status(self, mock_oauth_session):
        mock_session = MagicMock()
        mock_oauth_session.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "test_token"}

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_session.post.return_value = mock_response

        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )

        transport = HttpTransport(config)
        event = SecurityEvent(data="Test event")

        with pytest.raises(TransportError, match="POST request .* completed with status 400"):
            transport.send(event)

    @patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session')
    def test_send_network_error(self, mock_oauth_session):
        mock_session = MagicMock()
        mock_oauth_session.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "test_token"}

        mock_session.post.side_effect = requests.exceptions.ConnectionError("Network error")

        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )

        transport = HttpTransport(config)
        event = SecurityEvent(data="Test event")

        with pytest.raises(TransportError, match="Network error"):
            transport.send(event)

    @patch('sap_cloud_sdk.auditlog._http_transport.OAuth2Session')
    def test_send_unexpected_error(self, mock_oauth_session):
        mock_session = MagicMock()
        mock_oauth_session.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "test_token"}

        mock_session.post.side_effect = Exception("Unexpected error")

        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )

        transport = HttpTransport(config)
        event = SecurityEvent(data="Test event")

        with pytest.raises(TransportError, match="Unexpected error sending audit event"):
            transport.send(event)
