"""Unit tests for send_custom_event."""

from unittest.mock import MagicMock

from sap_cloud_sdk.core.auditlog_ng.helper import _emit_custom_event as send_custom_event
from sap_cloud_sdk.core.auditlog_ng.gen.sap.auditlog.auditevent.v2 import (
    auditevent_pb2 as pb,
)

_TENANT_UUID = "9e0d89c9-17cd-439d-8a8b-9c44d3d272f0"


class TestSendCustomEvent:
    def test_sends_zzz_custom_event(self):
        """send_custom_event builds and sends a ZzzCustomEvent."""
        mock_client = MagicMock()
        send_custom_event(mock_client, _TENANT_UUID, "MY_EVENT", {"key": "val"})
        mock_client.send.assert_called_once()
        event = mock_client.send.call_args[0][0]
        assert isinstance(event, pb.ZzzCustomEvent)
        assert event.common.tenant_id == _TENANT_UUID
        assert event.common.app_context["event_name"] == "MY_EVENT"

    def test_payload_includes_event_name_and_custom_keys(self):
        """send_custom_event merges event_name and caller payload into custom struct."""
        mock_client = MagicMock()
        send_custom_event(mock_client, _TENANT_UUID, "MY_EVENT", {"tool": "my-tool"})
        event = mock_client.send.call_args[0][0]
        fields = event.custom.struct_value.fields
        assert fields["event_name"].string_value == "MY_EVENT"
        assert fields["tool"].string_value == "my-tool"

    def test_sets_user_initiator_id_when_provided(self):
        """send_custom_event stamps user_id on common.user_initiator_id."""
        mock_client = MagicMock()
        send_custom_event(mock_client, _TENANT_UUID, "MY_EVENT", {}, user_id="user@example.com")
        event = mock_client.send.call_args[0][0]
        assert event.common.user_initiator_id == "user@example.com"

    def test_omits_user_initiator_id_when_none(self):
        """send_custom_event leaves user_initiator_id empty when user_id is None."""
        mock_client = MagicMock()
        send_custom_event(mock_client, _TENANT_UUID, "MY_EVENT", {})
        event = mock_client.send.call_args[0][0]
        assert event.common.user_initiator_id == ""

    def test_propagates_send_exception(self):
        """send_custom_event does not suppress exceptions from client.send."""
        mock_client = MagicMock()
        mock_client.send.side_effect = RuntimeError("send failed")
        try:
            send_custom_event(mock_client, _TENANT_UUID, "MY_EVENT", {})
            assert False, "Expected RuntimeError"
        except RuntimeError:
            pass
