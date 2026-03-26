"""Tests for audit log client implementation."""

import pytest
from unittest.mock import MagicMock, patch

from sap_cloud_sdk.core.auditlog.client import AuditLogClient
from sap_cloud_sdk.core.auditlog._transport import AuditMessage, Transport
from sap_cloud_sdk.core.auditlog.models import SecurityEvent, FailedMessage
from sap_cloud_sdk.core.auditlog.exceptions import (
    ClientCreationError,
    TransportError
)


class MockTransport(Transport):
    """Mock transport for testing."""

    def __init__(self):
        self.sent_events = []
        self.should_fail = False
        self.should_close = False
        self.closed = False

    def send(self, event):
        if self.should_fail:
            raise TransportError("Transport failed")
        self.sent_events.append(event)

    def close(self):
        if self.should_close:
            raise Exception("Close failed")
        self.closed = True


class TestAuditLogClient:

    def test_initialization_success(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        assert client._transport == transport

    def test_initialization_transport_failure(self):
        with patch.object(AuditLogClient, '__init__', wraps=AuditLogClient.__init__) as mock_init:
            mock_init.side_effect = Exception("Transport init failed")
            with pytest.raises(Exception, match="Transport init failed"):
                AuditLogClient(MockTransport())

    def test_log_success(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        event = SecurityEvent(data="Test event")

        client.log(event)

        assert len(transport.sent_events) == 1
        assert transport.sent_events[0] == event

    def test_log_validation_error(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        event = SecurityEvent(data="")

        with pytest.raises(ValueError):
            client.log(event)

        assert len(transport.sent_events) == 0

    def test_log_transport_error(self):
        transport = MockTransport()
        transport.should_fail = True
        client = AuditLogClient(transport)
        event = SecurityEvent(data="Test event")

        with pytest.raises(TransportError):
            client.log(event)

    def test_log_validates_before_sending(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        event = SecurityEvent(data="Test event")

        with patch.object(event, 'validate') as mock_validate:
            client.log(event)
            mock_validate.assert_called_once()

    def test_log_batch_all_success(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        events: list[AuditMessage] = [
            SecurityEvent(data="Event 1"),
            SecurityEvent(data="Event 2")
        ]

        failed = client.log_batch(events)

        assert len(failed) == 0
        assert len(transport.sent_events) == 2

    def test_log_batch_some_failures(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        events: list[AuditMessage] = [
            SecurityEvent(data="Valid event"),
            SecurityEvent(data=""),
            SecurityEvent(data="Another valid")
        ]

        failed = client.log_batch(events)

        assert len(failed) == 1
        assert len(transport.sent_events) == 2
        assert failed[0].message == events[1]
        assert "data must not be empty" in failed[0].error

    def test_log_batch_transport_failures(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        events: list[AuditMessage] = [
            SecurityEvent(data="Event 1"),
            SecurityEvent(data="Event 2")
        ]

        def failing_send(event):
            if event.data == "Event 2":
                raise TransportError("Network error")
            transport.sent_events.append(event)

        transport.send = failing_send  # ty: ignore[invalid-assignment]

        failed = client.log_batch(events)

        assert len(failed) == 1
        assert len(transport.sent_events) == 1
        assert failed[0].message == events[1]
        assert failed[0].error == "Network error"

    def test_log_batch_empty_list(self):
        transport = MockTransport()
        client = AuditLogClient(transport)

        failed = client.log_batch([])

        assert len(failed) == 0
        assert len(transport.sent_events) == 0

    def test_log_batch_mixed_failures(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        events: list[AuditMessage] = [
            SecurityEvent(data="Valid"),
            SecurityEvent(data=""),
            SecurityEvent(data="Also valid")
        ]

        def selective_fail(event):
            if event.data == "Also valid":
                raise TransportError("Transport error")
            transport.sent_events.append(event)

        transport.send = selective_fail  # ty: ignore[invalid-assignment]

        failed = client.log_batch(events)

        assert len(failed) == 2
        assert len(transport.sent_events) == 1

        validation_failure = next(f for f in failed if "data must not be empty" in f.error)
        transport_failure = next(f for f in failed if "Transport error" in f.error)

        assert validation_failure.message == events[1]
        assert transport_failure.message == events[2]

    def test_close_success(self):
        transport = MockTransport()
        client = AuditLogClient(transport)

        client.close()

        assert transport.closed is True

    def test_close_transport_close_failure(self):
        transport = MockTransport()
        transport.should_close = True
        client = AuditLogClient(transport)

        with pytest.raises(Exception, match="Close failed"):
            client.close()

    def test_context_manager_success(self):
        transport = MockTransport()

        with AuditLogClient(transport) as client:
            event = SecurityEvent(data="Test event")
            client.log(event)

        assert transport.closed is True
        assert len(transport.sent_events) == 1

    def test_context_manager_exception_in_block(self):
        transport = MockTransport()

        with pytest.raises(ValueError):
            with AuditLogClient(transport) as client:
                event = SecurityEvent(data="Test event")
                client.log(event)
                raise ValueError("Something went wrong")

        assert transport.closed is True
        assert len(transport.sent_events) == 1

    def test_context_manager_enter_returns_self(self):
        transport = MockTransport()
        client = AuditLogClient(transport)

        result = client.__enter__()

        assert result is client

    def test_context_manager_exit_calls_close(self):
        transport = MockTransport()
        client = AuditLogClient(transport)

        with patch.object(client, 'close') as mock_close:
            client.__exit__(None, None, None)
            mock_close.assert_called_once()

    def test_log_batch_preserves_event_order_in_failures(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        events: list[AuditMessage] = [
            SecurityEvent(data=""),
            SecurityEvent(data="Valid"),
            SecurityEvent(data="")
        ]

        failed = client.log_batch(events)

        assert len(failed) == 2
        assert failed[0].message == events[0]
        assert failed[1].message == events[2]
        assert len(transport.sent_events) == 1
        assert transport.sent_events[0] == events[1]

    def test_log_batch_returns_failed_message_objects(self):
        transport = MockTransport()
        client = AuditLogClient(transport)
        invalid_event = SecurityEvent(data="")

        failed = client.log_batch([invalid_event])

        assert len(failed) == 1
        assert isinstance(failed[0], FailedMessage)
        assert failed[0].message == invalid_event
        assert isinstance(failed[0].error, str)
