"""Tests for Agent Gateway URL validation helpers."""

import pytest

from sap_cloud_sdk.agentgateway._url import _require_same_origin, _validate_mcp_id
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError


class TestValidateMcpId:
    """Tests for _validate_mcp_id."""

    @pytest.mark.parametrize(
        "value",
        [
            "sap.mcpbuilder:apiResource:cost-center:v1",
            "9e88a0c4-ab32-46d8-b1d3-07cbcac11831",
            "server1",
            "250695",
            "sap.x:v1",
        ],
    )
    def test_accepts_valid_ids(self, value):
        """Accept real ORD IDs, UUIDs, and simple identifiers unchanged."""
        assert _validate_mcp_id(value, "ord_id") == value

    @pytest.mark.parametrize(
        "value",
        ["../x", "a/b", "a?x", "a#f", "a%2fb", "a@b", "a b", "", "   ", ".", ".."],
    )
    def test_rejects_metacharacters_and_traversal(self, value):
        """Reject empty values, path separators, and traversal segments."""
        with pytest.raises(AgentGatewaySDKError):
            _validate_mcp_id(value, "ord_id")


class TestRequireSameOrigin:
    """Tests for _require_same_origin."""

    def test_accepts_same_host_https(self):
        _require_same_origin(
            "https://agw.example.com/v1/mcp/x/y", "https://agw.example.com"
        )

    def test_accepts_same_host_with_matching_port(self):
        _require_same_origin(
            "https://agw.example.com:8443/v1/mcp", "https://agw.example.com:8443"
        )

    def test_is_case_insensitive_on_host(self):
        _require_same_origin(
            "https://AGW.Example.com/v1/mcp", "https://agw.example.com"
        )

    def test_rejects_http_scheme(self):
        with pytest.raises(AgentGatewaySDKError, match="https"):
            _require_same_origin(
                "http://agw.example.com/v1/mcp", "https://agw.example.com"
            )

    def test_rejects_different_host(self):
        with pytest.raises(
            AgentGatewaySDKError, match="not the trusted gateway origin"
        ):
            _require_same_origin(
                "https://attacker.example/collect", "https://agw.example.com"
            )

    def test_rejects_embedded_credentials(self):
        with pytest.raises(AgentGatewaySDKError, match="credentials"):
            _require_same_origin(
                "https://user:pw@agw.example.com/v1/mcp", "https://agw.example.com"
            )

    def test_rejects_url_without_host(self):
        with pytest.raises(AgentGatewaySDKError):
            _require_same_origin("https:///v1/mcp", "https://agw.example.com")

    def test_accepts_allow_listed_extra_host(self):
        _require_same_origin(
            "https://other.example/mcp",
            "https://agw.example.com",
            extra_allowed_hosts=("other.example",),
        )

    def test_still_rejects_non_allow_listed_host(self):
        with pytest.raises(AgentGatewaySDKError):
            _require_same_origin(
                "https://attacker.example/mcp",
                "https://agw.example.com",
                extra_allowed_hosts=("other.example",),
            )
