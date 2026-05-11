"""Unit tests for MCPTool dataclass."""

from sap_cloud_sdk.agentgateway import MCPTool


class TestMCPTool:
    """Tests for MCPTool dataclass."""

    def test_namespaced_name(self):
        """Test namespaced_name property."""
        tool = MCPTool(
            name="create_order",
            server_name="s4hana_procurement",
            description="Create purchase order",
            input_schema={"type": "object"},
            url="https://example.com/mcp",
        )

        assert tool.namespaced_name == "s4hana_procurement__create_order"

    def test_namespaced_name_with_special_chars(self):
        """Test namespaced_name sanitizes invalid characters to underscores."""
        tool = MCPTool(
            name="get-item",
            server_name="my-server",
            description="Get item",
            input_schema={},
            url="https://example.com/mcp",
        )

        assert tool.namespaced_name == "my-server__get-item"

    def test_namespaced_name_sanitizes_dots_and_colons(self):
        """Test that dots, colons, slashes are replaced with underscores."""
        tool = MCPTool(
            name="get/data",
            server_name="my.server:v1",
            description="Get data",
            input_schema={},
            url="https://example.com/mcp",
        )

        assert tool.namespaced_name == "my_server_v1__get_data"

    def test_namespaced_name_truncates_long_names(self):
        """Test that names over 64 chars are truncated to 55 + hash suffix."""
        tool = MCPTool(
            name="get_supplier_operational_eval_scores_by_region",
            server_name="sales_order_mcp_demo",
            description="Long name tool",
            input_schema={},
            url="https://example.com/mcp",
        )

        result = tool.namespaced_name
        assert len(result) == 64
        # First 55 chars are preserved from the sanitized name
        assert result[:55] == "sales_order_mcp_demo__get_supplier_operational_eval_sco"
        # Followed by underscore and 8-char hash
        assert result[55] == "_"
        assert len(result[56:]) == 8

    def test_namespaced_name_short_names_unchanged(self):
        """Test that short valid names pass through without modification."""
        tool = MCPTool(
            name="list_orders",
            server_name="myserver",
            description="List orders",
            input_schema={},
            url="https://example.com/mcp",
        )

        assert tool.namespaced_name == "myserver__list_orders"

    def test_namespaced_name_uniqueness_on_truncation(self):
        """Test that two different long names produce different truncated results."""
        tool_a = MCPTool(
            name="get_supplier_operational_eval_scores_by_region_east",
            server_name="sales_order_mcp_demo",
            description="Tool A",
            input_schema={},
            url="https://example.com/mcp",
        )
        tool_b = MCPTool(
            name="get_supplier_operational_eval_scores_by_region_west",
            server_name="sales_order_mcp_demo",
            description="Tool B",
            input_schema={},
            url="https://example.com/mcp",
        )

        assert tool_a.namespaced_name != tool_b.namespaced_name
        assert len(tool_a.namespaced_name) == 64
        assert len(tool_b.namespaced_name) == 64

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
