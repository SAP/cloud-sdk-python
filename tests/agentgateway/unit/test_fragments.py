"""Unit tests for agentgateway._fragments — _list_active_integrations and helpers."""

from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.agentgateway._fragments import _list_active_integrations
from sap_cloud_sdk.agentgateway import create_client, AgentGatewaySDKError
from sap_cloud_sdk.destination._models import Fragment, Label, Level


# ============================================================
# Helpers
# ============================================================


def _fragment(name: str = "sap-managed-runtime-agw-mcp-abc") -> Fragment:
    return Fragment(name=name, properties={})


def _label(key: str, value: str) -> Label:
    return Label(key=key, values=[value])


def _full_labels(gtid: str, system_type: str, ord_id: str) -> list[Label]:
    return [
        _label("sap-managed-runtime-gtid", gtid),
        _label("sap-managed-runtime-system-type", system_type),
        _label("sap-managed-runtime-ordid", ord_id),
        _label("sap-managed-runtime-type", "agw.mcp.server"),
    ]


# ============================================================
# Tests: _list_active_integrations (module-level function)
# ============================================================


class TestListConnectedSystems:
    def test_returns_entries_from_fragment_labels(self):
        frag1 = _fragment("frag-mcp-1")
        frag2 = _fragment("frag-a2a-2")
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = [frag1, frag2]
        mock_client.get_fragment_labels.side_effect = [
            _full_labels("gtid-1", "sap.pce", "sap-pce-apiResource-PA-v1"),
            _full_labels("gtid-2", "sap.s4", "sap-s4-apiResource-BP-v1"),
        ]

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            result = _list_active_integrations("my-tenant")

        assert len(result) == 2
        assert result[0] == {
            "global_tenant_id": "gtid-1",
            "system_type": "sap.pce",
            "integration_dependency": "sap-pce-apiResource-PA-v1",
        }
        assert result[1] == {
            "global_tenant_id": "gtid-2",
            "system_type": "sap.s4",
            "integration_dependency": "sap-s4-apiResource-BP-v1",
        }

    def test_returns_empty_list_when_no_fragments(self):
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = []

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            result = _list_active_integrations("my-tenant")

        assert result == []
        mock_client.get_fragment_labels.assert_not_called()

    def test_returns_none_system_type_when_label_absent(self):
        frag = _fragment("frag-no-systype")
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = [frag]
        mock_client.get_fragment_labels.return_value = [
            _label("sap-managed-runtime-gtid", "gtid-1"),
            _label("sap-managed-runtime-ordid", "sap-pce-apiResource-PA-v1"),
        ]

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            result = _list_active_integrations("my-tenant")

        assert len(result) == 1
        assert result[0] == {
            "global_tenant_id": "gtid-1",
            "system_type": None,
            "integration_dependency": "sap-pce-apiResource-PA-v1",
        }

    def test_fragment_with_missing_labels_gets_none_values(self):
        frag_ok = _fragment("frag-ok")
        frag_partial = _fragment("frag-partial")
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = [frag_ok, frag_partial]
        mock_client.get_fragment_labels.side_effect = [
            _full_labels("gtid-ok", "sap.pce", "sap-pce-apiResource-PA-v1"),
            [_label("sap-managed-runtime-gtid", "gtid-partial")],  # missing system_type and ord_id
        ]

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            result = _list_active_integrations("my-tenant")

        assert len(result) == 2
        assert result[0] == {
            "global_tenant_id": "gtid-ok",
            "system_type": "sap.pce",
            "integration_dependency": "sap-pce-apiResource-PA-v1",
        }
        assert result[1] == {
            "global_tenant_id": "gtid-partial",
            "system_type": None,
            "integration_dependency": None,
        }

    def test_passes_tenant_subdomain_to_list_and_get_labels(self):
        frag = _fragment("frag-abc")
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = [frag]
        mock_client.get_fragment_labels.return_value = _full_labels(
            "gtid-1", "sap.pce", "sap-pce-apiResource-PA-v1"
        )

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            _list_active_integrations("specific-tenant")

        list_kwargs = mock_client.list_instance_fragments.call_args.kwargs
        assert list_kwargs["tenant"] == "specific-tenant"

        get_kwargs = mock_client.get_fragment_labels.call_args.kwargs
        assert get_kwargs["tenant"] == "specific-tenant"

    def test_get_fragment_labels_called_with_service_instance_level(self):
        frag = _fragment("frag-abc")
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = [frag]
        mock_client.get_fragment_labels.return_value = _full_labels(
            "gtid-1", "sap.pce", "sap-pce-apiResource-PA-v1"
        )

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            _list_active_integrations("my-tenant")

        get_kwargs = mock_client.get_fragment_labels.call_args.kwargs
        assert get_kwargs["level"] == Level.SERVICE_INSTANCE

    def test_get_fragment_labels_called_once_per_fragment(self):
        frags = [_fragment(f"frag-{i}") for i in range(3)]
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = frags
        mock_client.get_fragment_labels.return_value = _full_labels(
            "gtid-x", "sap.pce", "sap-pce-apiResource-PA-v1"
        )

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            _list_active_integrations("my-tenant")

        assert mock_client.get_fragment_labels.call_count == 3

    def test_filters_by_mcp_label_type_only(self):
        from sap_cloud_sdk.destination._models import ListOptions

        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = []

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            _list_active_integrations("my-tenant")

        call_kwargs = mock_client.list_instance_fragments.call_args.kwargs
        filter_obj: ListOptions = call_kwargs["filter"]
        assert filter_obj is not None
        assert filter_obj.filter_labels is not None
        assert len(filter_obj.filter_labels) == 1
        label: Label = filter_obj.filter_labels[0]
        assert label.key == "sap-managed-runtime-type"
        assert "agw.mcp.server" in label.values
        assert "agw.a2a.server" not in label.values


# ============================================================
# Tests: AgentGatewayClient.list_active_integrations
# ============================================================


class TestAgentGatewayClientListConnectedSystems:
    def test_delegates_to_fragments_helper(self):
        expected = [
            {
                "global_tenant_id": "gtid-1",
                "system_type": "sap.pce",
                "integration_dependency": "sap-pce-apiResource-PA-v1",
            }
        ]
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_transparent_credentials",
                return_value=False,
            ),
            patch.object(
                __import__("sap_cloud_sdk.agentgateway._fragments", fromlist=["_list_active_integrations"]),
                "_list_active_integrations",
                return_value=expected,
            ) as mock_fn,
        ):
            client = create_client(tenant_subdomain="my-tenant")
            result = client.list_active_integrations()

        assert result == expected
        mock_fn.assert_called_once_with("my-tenant")

    def test_returns_empty_list_when_no_integrations(self):
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_transparent_credentials",
                return_value=False,
            ),
            patch.object(
                __import__("sap_cloud_sdk.agentgateway._fragments", fromlist=["_list_active_integrations"]),
                "_list_active_integrations",
                return_value=[],
            ),
        ):
            client = create_client(tenant_subdomain="my-tenant")
            result = client.list_active_integrations()

        assert result == []

    def test_raises_when_tenant_subdomain_not_configured(self):
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_transparent_credentials",
                return_value=False,
            ),
        ):
            client = create_client()
            with pytest.raises(AgentGatewaySDKError):
                client.list_active_integrations()

    def test_raises_for_standard_customer_agent(self):
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value="/etc/secrets/credentials.json",
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_transparent_credentials",
                return_value=False,
            ),
        ):
            client = create_client(tenant_subdomain="my-tenant")
            with pytest.raises(AgentGatewaySDKError, match="not supported for customer agents"):
                client.list_active_integrations()

    def test_raises_for_transparent_customer_agent(self):
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_customer_agent_credentials",
                return_value=None,
            ),
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_transparent_credentials",
                return_value=True,
            ),
        ):
            client = create_client(tenant_subdomain="my-tenant")
            with pytest.raises(AgentGatewaySDKError, match="not supported for customer agents"):
                client.list_active_integrations()
