"""Tests for HTTP transport implementation."""

import pytest
from unittest.mock import patch, MagicMock
import requests

from sap_cloud_sdk.core.auditlog._http_transport import HttpTransport
from sap_cloud_sdk.core.auditlog._transport import Transport
from sap_cloud_sdk.core.auditlog.config import AuditLogConfig
from sap_cloud_sdk.core.auditlog.models import (
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
    DataAccessAttribute
)
from sap_cloud_sdk.core.auditlog.exceptions import TransportError, AuthenticationError


class TestHttpTransport:

    def test_inherits_from_transport(self):
        assert issubclass(HttpTransport, Transport)

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
    def test_initialization_success(self, mock_oauth_session):
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
        assert transport.config == config
        assert transport.oauth is None  # lazy — no session yet

        transport.send(SecurityEvent(data="init test"))
        mock_session.fetch_token.assert_called_once_with(
            token_url="https://oauth.example.com/oauth/token",
            client_id="test_client",
            client_secret="test_secret"
        )

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
    def test_initialization_oauth_url_with_trailing_slash(self, mock_oauth_session):
        mock_session = MagicMock()
        mock_oauth_session.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "test_token"}
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.post.return_value = mock_response

        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com/",
            service_url="https://service.example.com"
        )

        transport = HttpTransport(config)
        transport.send(SecurityEvent(data="trailing slash test"))

        mock_session.fetch_token.assert_called_once_with(
            token_url="https://oauth.example.com/oauth/token",
            client_id="test_client",
            client_secret="test_secret"
        )

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
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

        transport = HttpTransport(config)
        with pytest.raises(TransportError):
            transport.send(SecurityEvent(data="auth fail test"))

    def test_get_endpoint_security_event(self):
        with patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session') as mock_oauth:
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
        with patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session') as mock_oauth:
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
        with patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session') as mock_oauth:
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
        with patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session') as mock_oauth:
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
        with patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session') as mock_oauth:
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
        with patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session') as mock_oauth:
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
        with patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session') as mock_oauth:
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

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
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

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
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

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
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

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
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

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
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


class TestHttpTransportRotation:

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
    def test_proactive_rotation_rebuilds_session_when_binding_changed(self, mock_oauth):
        original_config = AuditLogConfig(
            client_id="old-client",
            client_secret="old-secret",
            oauth_url="https://old-oauth.example.com",
            service_url="https://service.example.com",
        )
        new_config = AuditLogConfig(
            client_id="new-client",
            client_secret="new-secret",
            oauth_url="https://new-oauth.example.com",
            service_url="https://service.example.com",
        )

        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "new-token"}
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.post.return_value = mock_response

        mock_factory = MagicMock(return_value=original_config)
        mock_factory.has_changed = MagicMock(return_value=True)
        mock_factory.return_value = new_config

        transport = HttpTransport(mock_factory)
        transport.send(SecurityEvent(data="rotation test"))

        assert transport.config is new_config
        # factory called once at init, once on rotation
        assert mock_factory.call_count == 2

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
    def test_no_rebuild_when_binding_unchanged(self, mock_oauth):
        config = AuditLogConfig(
            client_id="client",
            client_secret="secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com",
        )
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "tok"}
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.post.return_value = mock_response

        mock_factory = MagicMock(return_value=config)
        mock_factory.has_changed = MagicMock(return_value=False)

        transport = HttpTransport(mock_factory)
        transport.send(SecurityEvent(data="no rotation"))
        oauth_after_first = transport.oauth

        transport.send(SecurityEvent(data="second call"))

        mock_factory.has_changed.assert_called()
        assert mock_factory.call_count == 1  # no extra factory call
        assert transport.oauth is oauth_after_first  # same session

    @patch('sap_cloud_sdk.core.auditlog._http_transport.OAuth2Session')
    def test_static_config_skips_rotation_check(self, mock_oauth):
        config = AuditLogConfig(
            client_id="client",
            client_secret="secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com",
        )
        mock_session = MagicMock()
        mock_oauth.return_value = mock_session
        mock_session.fetch_token.return_value = {"access_token": "tok"}
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.post.return_value = mock_response

        transport = HttpTransport(config)
        transport.send(SecurityEvent(data="static config"))

        # No has_changed on plain AuditLogConfig — no error, session created once
        assert transport.oauth is mock_session
