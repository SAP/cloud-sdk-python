"""Unit tests for MCPTool dataclass."""

from sap_cloud_sdk.agentgateway import MCPTool


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
