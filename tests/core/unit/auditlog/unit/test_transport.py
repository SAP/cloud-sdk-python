"""Tests for transport layer abstraction."""

import pytest
from abc import ABC

from sap_cloud_sdk.core.auditlog._transport import Transport, AuditMessage
from sap_cloud_sdk.core.auditlog.models import SecurityEvent, DataAccessEvent
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
