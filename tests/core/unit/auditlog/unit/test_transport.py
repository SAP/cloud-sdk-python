"""Tests for transport layer abstraction and HTTP implementation."""

import pytest
from abc import ABC
from unittest.mock import patch, MagicMock

from sap_cloud_sdk.core.auditlog._transport import Transport, HttpTransport, AuditMessage
from sap_cloud_sdk.core.auditlog.config import AuditLogConfig
from sap_cloud_sdk.core.auditlog.models import (
    SecurityEvent,
    DataAccessEvent,
    DataModificationEvent,
    ConfigurationChangeEvent,
    DataDeletionEvent,
    ConfigurationDeletionEvent,
    DataAccessAttribute,
)
from sap_cloud_sdk.core.auditlog.exceptions import TransportError


class TestTransport:

    def test_is_abstract_base_class(self):
        assert issubclass(Transport, ABC)

        with pytest.raises(TypeError):
            Transport()

    def test_abstract_send_method(self):
        assert hasattr(Transport, 'send')
        assert getattr(Transport.send, '__isabstractmethod__', False)


class TestAuditMessage:

    def test_audit_message_type_alias(self):
        security_event = SecurityEvent(data="test")
        data_access_event = DataAccessEvent(
            object_type="database",
            object_id={"table": "users"},
            subject_type="user",
            subject_id={"id": "123"},
            attributes=[]
        )

        assert isinstance(security_event, (SecurityEvent, DataAccessEvent))
        assert isinstance(data_access_event, (SecurityEvent, DataAccessEvent))


class ConcreteTransport(Transport):
    """Concrete implementation for testing."""

    def __init__(self):
        self.sent_events = []
        self.should_fail = False

    def send(self, event: AuditMessage) -> None:
        if self.should_fail:
            raise TransportError("Transport failed")
        self.sent_events.append(event)


class TestConcreteTransport:

    def test_concrete_implementation(self):
        transport = ConcreteTransport()
        event = SecurityEvent(data="test")

        transport.send(event)

        assert len(transport.sent_events) == 1
        assert transport.sent_events[0] == event

    def test_concrete_implementation_failure(self):
        transport = ConcreteTransport()
        transport.should_fail = True
        event = SecurityEvent(data="test")

        with pytest.raises(TransportError, match="Transport failed"):
            transport.send(event)

        assert len(transport.sent_events) == 0


def _config(**overrides) -> AuditLogConfig:
    defaults = dict(
        client_id="test_client",
        client_secret="test_secret",
        oauth_url="https://oauth.example.com",
        service_url="https://service.example.com",
    )
    defaults.update(overrides)
    return AuditLogConfig(**defaults)


def _ok_response(status_code: int = 201):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = ""
    return resp


def _error_response(status_code: int, text: str = "error"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


class TestHttpTransport:

    def test_inherits_from_transport(self):
        assert issubclass(HttpTransport, Transport)

    @patch("sap_cloud_sdk.core.auditlog._transport.HttpClient")
    @patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider")
    def test_initialization_creates_http_client(self, mock_auth_cls, mock_client_cls):
        config = _config()
        HttpTransport(config)

        mock_auth_cls.assert_called_once()
        mock_client_cls.assert_called_once_with(config.service_url, mock_auth_cls.return_value)

    @patch("sap_cloud_sdk.core.auditlog._transport.HttpClient")
    @patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider")
    def test_send_posts_to_correct_endpoint(self, mock_auth_cls, mock_client_cls):
        mock_http = MagicMock()
        mock_client_cls.return_value = mock_http
        mock_http.request.return_value = _ok_response()

        transport = HttpTransport(_config())
        event = SecurityEvent(data="test event")
        transport.send(event)

        mock_http.request.assert_called_once()
        args, kwargs = mock_http.request.call_args
        assert "/audit-log/oauth2/v2/security-events" in args[1]
        assert kwargs["json"] == event.to_dict()
        assert kwargs["headers"] == {"Content-Type": "application/json"}

    @patch("sap_cloud_sdk.core.auditlog._transport.HttpClient")
    @patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider")
    def test_send_http_error_status_raises_transport_error(self, mock_auth_cls, mock_client_cls):
        mock_http = MagicMock()
        mock_client_cls.return_value = mock_http
        mock_http.request.return_value = _error_response(400, "Bad Request")

        transport = HttpTransport(_config())
        with pytest.raises(TransportError, match="status 400"):
            transport.send(SecurityEvent(data="test"))

    @patch("sap_cloud_sdk.core.auditlog._transport.HttpClient")
    @patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider")
    def test_send_unexpected_exception_raises_transport_error(self, mock_auth_cls, mock_client_cls):
        mock_http = MagicMock()
        mock_client_cls.return_value = mock_http
        mock_http.request.side_effect = Exception("Unexpected error")

        transport = HttpTransport(_config())
        with pytest.raises(TransportError, match="Unexpected error sending audit event"):
            transport.send(SecurityEvent(data="test"))

    @patch("sap_cloud_sdk.core.auditlog._transport.HttpClient")
    @patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider")
    def test_send_service_url_trailing_slash_stripped(self, mock_auth_cls, mock_client_cls):
        mock_http = MagicMock()
        mock_client_cls.return_value = mock_http
        mock_http.request.return_value = _error_response(500, "err")

        transport = HttpTransport(_config(service_url="https://service.example.com/"))
        with pytest.raises(TransportError) as exc_info:
            transport.send(SecurityEvent(data="test"))

        assert "https://service.example.com/audit-log/oauth2/v2/security-events" in str(exc_info.value)

    def test_get_endpoint_security_event(self):
        with patch("sap_cloud_sdk.core.auditlog._transport.HttpClient"), \
             patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider"):
            transport = HttpTransport(_config())
            assert transport._get_endpoint(SecurityEvent(data="x")) == "/security-events"

    def test_get_endpoint_data_access_event(self):
        with patch("sap_cloud_sdk.core.auditlog._transport.HttpClient"), \
             patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider"):
            transport = HttpTransport(_config())
            event = DataAccessEvent(
                object_type="db",
                object_id={"table": "users"},
                subject_type="user",
                subject_id={"id": "1"},
                attributes=[DataAccessAttribute("email")],
            )
            assert transport._get_endpoint(event) == "/data-accesses"

    def test_get_endpoint_data_modification_event(self):
        with patch("sap_cloud_sdk.core.auditlog._transport.HttpClient"), \
             patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider"):
            transport = HttpTransport(_config())
            event = DataModificationEvent(
                object_type="profile", object_id={"id": "1"},
                subject_type="user", subject_id={"id": "2"}, attributes=[],
            )
            assert transport._get_endpoint(event) == "/data-modifications"

    def test_get_endpoint_data_deletion_event(self):
        with patch("sap_cloud_sdk.core.auditlog._transport.HttpClient"), \
             patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider"):
            transport = HttpTransport(_config())
            event = DataDeletionEvent(
                object_type="profile", object_id={"id": "1"},
                subject_type="user", subject_id={"id": "2"}, attributes=[],
            )
            assert transport._get_endpoint(event) == "/data-modifications"

    def test_get_endpoint_configuration_change_event(self):
        with patch("sap_cloud_sdk.core.auditlog._transport.HttpClient"), \
             patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider"):
            transport = HttpTransport(_config())
            event = ConfigurationChangeEvent(
                object_type="config", object_id={"s": "t"}, attributes=[]
            )
            assert transport._get_endpoint(event) == "/configuration-changes"

    def test_get_endpoint_configuration_deletion_event(self):
        with patch("sap_cloud_sdk.core.auditlog._transport.HttpClient"), \
             patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider"):
            transport = HttpTransport(_config())
            event = ConfigurationDeletionEvent(
                object_type="config", object_id={"s": "t"}, attributes=[]
            )
            assert transport._get_endpoint(event) == "/configuration-changes"

    def test_get_endpoint_unknown_event_raises(self):
        with patch("sap_cloud_sdk.core.auditlog._transport.HttpClient"), \
             patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider"):
            transport = HttpTransport(_config())

            class UnknownEvent:
                pass

            with pytest.raises(TransportError, match="Unknown event type"):
                transport._get_endpoint(UnknownEvent())  # ty: ignore[invalid-argument-type]


class TestHttpTransportRotation:

    @patch("sap_cloud_sdk.core.auditlog._transport.HttpClient")
    @patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider")
    def test_proactive_rotation_handled_by_xsuaa_provider(self, mock_auth_cls, mock_client_cls):
        """XsuaaAuthProvider is instantiated with the factory — rotation is its responsibility."""
        new_config = _config(client_id="new-client", client_secret="new-secret")
        mock_factory = MagicMock(return_value=new_config)
        mock_factory.has_changed = MagicMock(return_value=True)

        mock_http = MagicMock()
        mock_client_cls.return_value = mock_http
        mock_http.request.return_value = _ok_response()

        HttpTransport(mock_factory)

        mock_auth_cls.assert_called_once_with(mock_factory)

    @patch("sap_cloud_sdk.core.auditlog._transport.HttpClient")
    @patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider")
    def test_static_config_creates_lambda_factory_for_provider(self, mock_auth_cls, mock_client_cls):
        """A plain AuditLogConfig is wrapped in a lambda before being passed to XsuaaAuthProvider."""
        config = _config()
        HttpTransport(config)

        auth_factory_arg = mock_auth_cls.call_args[0][0]
        assert callable(auth_factory_arg)
        assert auth_factory_arg() is config

    @patch("sap_cloud_sdk.core.auditlog._transport.HttpClient")
    @patch("sap_cloud_sdk.core.auditlog._transport.XsuaaAuthProvider")
    def test_send_multiple_events_reuses_http_client(self, mock_auth_cls, mock_client_cls):
        mock_http = MagicMock()
        mock_client_cls.return_value = mock_http
        mock_http.request.return_value = _ok_response()

        transport = HttpTransport(_config())
        transport.send(SecurityEvent(data="first"))
        transport.send(SecurityEvent(data="second"))

        assert mock_http.request.call_count == 2
        assert mock_client_cls.call_count == 1
