"""Tests for extensibility audit helpers and ExtensibilityClient.audit_instruction_applied."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from sap_cloud_sdk.extensibility._models import ExtensionCapabilityImplementation
from sap_cloud_sdk.extensibility.client import ExtensibilityClient


def _make_client(*, channel_id: str = "", service_name: str = "") -> ExtensibilityClient:
    transport = MagicMock()
    transport.get_extension_capability_implementation.return_value = (
        ExtensionCapabilityImplementation(capability_id="default")
    )
    return ExtensibilityClient(
        transport,
        _audit_channel_id=channel_id,
        _audit_service_name=service_name,
    )


def _run(coro):
    return asyncio.run(coro)


class TestAuditInternalHelpers:
    def test_emit_hook_executed_no_ops_when_no_channel(self):
        from sap_cloud_sdk.extensibility._audit import _emit_hook_executed

        with patch(
            "sap_cloud_sdk.extensibility._audit._make_client", new=MagicMock()
        ) as mock_make:
            _run(
                _emit_hook_executed(
                    phase="pre",
                    tenant_subdomain="",
                    tenant_id="t",
                    user_id="u",
                    hook_name="h",
                    capability_id="cap",
                    channel_id="",
                    service_name="svc",
                )
            )
        mock_make.assert_not_called()

    def test_emit_instruction_applied_no_ops_when_no_subdomain(self):
        from sap_cloud_sdk.extensibility._audit import _emit_instruction_applied

        with patch(
            "sap_cloud_sdk.extensibility._audit._make_client", new=MagicMock()
        ) as mock_make:
            _run(
                _emit_instruction_applied(
                    tenant_subdomain="",
                    tenant_id="t",
                    user_id="u",
                    context_id="ctx",
                    capability_id="cap",
                    channel_id="my-agent",
                    service_name="svc",
                )
            )
        mock_make.assert_not_called()

    def test_emit_hook_short_circuit_no_ops_when_no_channel(self):
        from sap_cloud_sdk.extensibility._audit import _emit_hook_short_circuit

        with patch(
            "sap_cloud_sdk.extensibility._audit._make_client", new=MagicMock()
        ) as mock_make:
            _run(
                _emit_hook_short_circuit(
                    tenant_subdomain="sub",
                    tenant_id="t",
                    user_id="u",
                    hook_name="h",
                    capability_id="cap",
                    reason="blocked",
                    channel_id="",
                    service_name="svc",
                )
            )
        mock_make.assert_not_called()


class TestAuditInstructionApplied:
    def test_no_op_when_no_channel_id(self):
        client = _make_client(channel_id="")
        with patch(
            "sap_cloud_sdk.extensibility._audit._emit_instruction_applied",
            new=AsyncMock(),
        ) as mock_emit:
            _run(
                client.audit_instruction_applied(
                    tenant_subdomain="sub",
                    tenant_id="t",
                    context_id="ctx",
                )
            )
        mock_emit.assert_not_called()

    def test_emits_when_channel_id_set(self):
        client = _make_client(channel_id="my-agent", service_name="my-svc")
        with patch(
            "sap_cloud_sdk.extensibility._audit._emit_instruction_applied",
            new=AsyncMock(),
        ) as mock_emit:
            _run(
                client.audit_instruction_applied(
                    tenant_subdomain="sub",
                    tenant_id="tid",
                    context_id="ctx-1",
                    capability_id="cap-a",
                    user_id="user@test.com",
                )
            )
        mock_emit.assert_called_once()
        kw = mock_emit.call_args[1]
        assert kw["tenant_subdomain"] == "sub"
        assert kw["context_id"] == "ctx-1"
        assert kw["capability_id"] == "cap-a"
        assert kw["channel_id"] == "my-agent"
        assert kw["service_name"] == "my-svc"

    def test_service_name_falls_back_to_channel_id(self):
        client = _make_client(channel_id="my-agent", service_name="")
        assert client._audit_service_name == "my-agent"
