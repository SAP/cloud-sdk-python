"""Unit tests for agentgateway dataclasses."""

from sap_cloud_sdk.agentgateway import MCPTool
from sap_cloud_sdk.agentgateway._models import CustomerCredentials


class TestMCPTool:
    """Tests for MCPTool dataclass."""

    def test_create_tool_with_all_fields(self):
        """Test MCPTool creation with all fields."""
        tool = MCPTool(
            name="test_tool",
            server_name="test_server",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {"param1": {"type": "string"}},
            },
            url="https://example.com/mcp",
            fragment_name="test-fragment",
        )

        assert tool.name == "test_tool"
        assert tool.server_name == "test_server"
        assert tool.description == "A test tool"
        assert tool.input_schema == {
            "type": "object",
            "properties": {"param1": {"type": "string"}},
        }
        assert tool.url == "https://example.com/mcp"
        assert tool.fragment_name == "test-fragment"

    def test_create_tool_without_fragment_name(self):
        """Test MCPTool creation without fragment_name defaults to None."""
        tool = MCPTool(
            name="simple_tool",
            server_name="server",
            description="Simple tool",
            input_schema={},
            url="https://example.com/mcp",
        )

        assert tool.fragment_name is None

    def test_create_tool_with_empty_input_schema(self):
        """Test MCPTool creation with empty input schema."""
        tool = MCPTool(
            name="simple_tool",
            server_name="server",
            description="Simple tool",
            input_schema={},
            url="https://example.com/mcp",
        )

        assert tool.input_schema == {}


class TestCustomerCredentials:
    """Tests for CustomerCredentials dataclass."""

    def test_repr_omits_certificate_and_private_key(self):
        """Test that credential values never appear in the repr (CWE-532)."""
        creds = CustomerCredentials(
            token_service_url="https://ias.example.com",
            client_id="id",
            gateway_url="https://agw.example.com",
            integration_dependencies=[],
            certificate="cert-pem",
            private_key="key-pem",
        )

        rendered = repr(creds)

        assert "cert-pem" not in rendered
        assert "key-pem" not in rendered
