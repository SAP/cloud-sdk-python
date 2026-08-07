"""Unit tests for agentgateway._fragments — list_active_integrations and helpers."""

from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.agentgateway._fragments import (
    _parse_integration_from_url,
    list_active_integrations,
)
from sap_cloud_sdk.agentgateway import create_client, AgentGatewaySDKError
from sap_cloud_sdk.destination._models import Fragment


# ============================================================
# Helpers
# ============================================================


def _fragment(url: str, name: str = "sap-managed-runtime-agw-mcp-abc") -> Fragment:
    return Fragment(name=name, properties={"URL": url})


# ============================================================
# Tests: _parse_integration_from_url
# ============================================================


class TestParseIntegrationFromUrl:
    def test_mcp_url_returns_correct_fields(self):
        url = "https://agw.example.com/v1/mcp/sap.pce:apiResource:PA:v1/gtid-123"
        result = _parse_integration_from_url(url)
        assert result == {
            "global_tenant_id": "gtid-123",
            "system_type": "sap.pce",
            "integration_dependency": "sap.pce:apiResource:PA:v1",
        }

    def test_a2a_url_returns_correct_fields(self):
        url = "https://agw.example.com/v1/a2a/sap.s4:apiResource:BP:v1/gtid-456"
        result = _parse_integration_from_url(url)
        assert result == {
            "global_tenant_id": "gtid-456",
            "system_type": "sap.s4",
            "integration_dependency": "sap.s4:apiResource:BP:v1",
        }

    def test_ord_id_with_slash_segments(self):
        url = "https://agw.example.com/v1/mcp/sap.sf:apiResource:jobs/v1/gtid-789"
        result = _parse_integration_from_url(url)
        assert result == {
            "global_tenant_id": "gtid-789",
            "system_type": "sap.sf",
            "integration_dependency": "sap.sf:apiResource:jobs/v1",
        }

    def test_trailing_slash_is_ignored(self):
        url = "https://agw.example.com/v1/mcp/sap.pce:apiResource:PA:v1/gtid-123/"
        result = _parse_integration_from_url(url)
        assert result is not None
        assert result["global_tenant_id"] == "gtid-123"

    def test_returns_none_for_url_without_v1_mode(self):
        url = "https://agw.example.com/some/other/path/gtid-123"
        assert _parse_integration_from_url(url) is None

    def test_returns_none_for_empty_url(self):
        assert _parse_integration_from_url("") is None

    def test_returns_none_when_nothing_after_mode(self):
        url = "https://agw.example.com/v1/mcp/"
        assert _parse_integration_from_url(url) is None

    def test_returns_none_when_only_gtid_after_mode(self):
        # mode_idx + 2 > len(parts) - 1  →  no ord_id between mode and gtid
        url = "https://agw.example.com/v1/mcp/gtid-only"
        assert _parse_integration_from_url(url) is None


# ============================================================
# Tests: list_active_integrations (module-level function)
# ============================================================


class TestListActiveIntegrations:
    def test_returns_parsed_entries_for_matching_fragments(self):
        fragments = [
            _fragment("https://agw.example.com/v1/mcp/sap.pce:apiResource:PA:v1/gtid-1"),
            _fragment("https://agw.example.com/v1/a2a/sap.s4:apiResource:BP:v1/gtid-2"),
        ]
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = fragments

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            result = list_active_integrations("my-tenant")

        assert len(result) == 2
        assert result[0] == {
            "global_tenant_id": "gtid-1",
            "system_type": "sap.pce",
            "integration_dependency": "sap.pce:apiResource:PA:v1",
        }
        assert result[1] == {
            "global_tenant_id": "gtid-2",
            "system_type": "sap.s4",
            "integration_dependency": "sap.s4:apiResource:BP:v1",
        }

    def test_returns_empty_list_when_no_fragments(self):
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = []

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            result = list_active_integrations("my-tenant")

        assert result == []

    def test_skips_fragments_with_unparseable_url(self):
        fragments = [
            _fragment("https://agw.example.com/some/unrelated/path"),
            _fragment("https://agw.example.com/v1/mcp/sap.pce:apiResource:PA:v1/gtid-1"),
        ]
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = fragments

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            result = list_active_integrations("my-tenant")

        assert len(result) == 1
        assert result[0]["global_tenant_id"] == "gtid-1"

    def test_skips_fragments_with_missing_url_property(self):
        fragment = Fragment(name="sap-managed-runtime-agw-mcp-abc", properties={})
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = [fragment]

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            result = list_active_integrations("my-tenant")

        assert result == []

    def test_passes_tenant_subdomain_to_fragment_client(self):
        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = []

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            list_active_integrations("specific-tenant")

        call_kwargs = mock_client.list_instance_fragments.call_args.kwargs
        assert call_kwargs["tenant"] == "specific-tenant"

    def test_filters_by_mcp_and_a2a_label_types(self):
        from sap_cloud_sdk.destination._models import Label, ListOptions

        mock_client = MagicMock()
        mock_client.list_instance_fragments.return_value = []

        with patch(
            "sap_cloud_sdk.agentgateway._fragments.create_fragment_client",
            return_value=mock_client,
        ):
            list_active_integrations("my-tenant")

        call_kwargs = mock_client.list_instance_fragments.call_args.kwargs
        filter_obj: ListOptions = call_kwargs["filter"]
        assert filter_obj is not None
        assert len(filter_obj.filter_labels) == 1
        label: Label = filter_obj.filter_labels[0]
        assert label.key == "sap-managed-runtime-type"
        assert "agw.mcp.server" in label.values
        assert "agw.a2a.server" in label.values


# ============================================================
# Tests: AgentGatewayClient.list_active_integrations
# ============================================================


class TestAgentGatewayClientListActiveIntegrations:
    def test_delegates_to_fragments_helper(self):
        expected = [
            {
                "global_tenant_id": "gtid-1",
                "system_type": "sap.pce",
                "integration_dependency": "sap.pce:apiResource:PA:v1",
            }
        ]
        with (
            patch(
                "sap_cloud_sdk.agentgateway.agw_client.detect_transparent_credentials",
                return_value=False,
            ),
            patch.object(
                __import__("sap_cloud_sdk.agentgateway._fragments", fromlist=["list_active_integrations"]),
                "list_active_integrations",
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
                "sap_cloud_sdk.agentgateway.agw_client.detect_transparent_credentials",
                return_value=False,
            ),
            patch.object(
                __import__("sap_cloud_sdk.agentgateway._fragments", fromlist=["list_active_integrations"]),
                "list_active_integrations",
                return_value=[],
            ),
        ):
            client = create_client(tenant_subdomain="my-tenant")
            result = client.list_active_integrations()

        assert result == []

    def test_raises_when_tenant_subdomain_not_configured(self):
        with patch(
            "sap_cloud_sdk.agentgateway.agw_client.detect_transparent_credentials",
            return_value=False,
        ):
            client = create_client()
            with pytest.raises(AgentGatewaySDKError):
                client.list_active_integrations()
