"""Unit tests for MCP tool converters."""

from unittest.mock import AsyncMock

from sap_cloud_sdk.agentgateway import MCPTool
from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain


class TestMcpToolToLangchain:
    """Tests for mcp_tool_to_langchain converter."""

    def test_creates_structured_tool(self):
        """Create LangChain StructuredTool from MCPTool."""
        tool = MCPTool(
            name="create_order",
            server_name="s4hana",
            description="Create a purchase order",
            input_schema={
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
            },
            url="https://example.com/mcp",
        )

        call_tool = AsyncMock(return_value="result")
        get_user_token = lambda: "user-jwt"

        result = mcp_tool_to_langchain(tool, call_tool, get_user_token)

        assert result.name == "s4hana__create_order"
        assert result.description == "Create a purchase order"
        assert result.coroutine is not None

    def test_creates_args_schema_from_input_schema(self):
        """Create args schema from MCPTool input schema properties."""
        tool = MCPTool(
            name="test_tool",
            server_name="server",
            description="Test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"},
                },
            },
            url="https://example.com/mcp",
        )

        call_tool = AsyncMock(return_value="result")

        result = mcp_tool_to_langchain(tool, call_tool, lambda: "token")

        assert result.args_schema is not None
        from pydantic import BaseModel

        assert isinstance(result.args_schema, type) and issubclass(
            result.args_schema, BaseModel
        )
        schema_fields = result.args_schema.model_fields
        assert "param1" in schema_fields
        assert "param2" in schema_fields

    def test_handles_empty_input_schema(self):
        """Handle MCPTool with empty input schema."""
        tool = MCPTool(
            name="simple_tool",
            server_name="server",
            description="Simple tool with no params",
            input_schema={},
            url="https://example.com/mcp",
        )

        call_tool = AsyncMock(return_value="result")

        result = mcp_tool_to_langchain(tool, call_tool, lambda: "token")

        assert result.name == "server__simple_tool"
        assert result.args_schema is not None

    def test_handles_input_schema_without_properties(self):
        """Handle MCPTool with input schema but no properties."""
        tool = MCPTool(
            name="tool",
            server_name="server",
            description="Tool",
            input_schema={"type": "object"},
            url="https://example.com/mcp",
        )

        call_tool = AsyncMock(return_value="result")

        result = mcp_tool_to_langchain(tool, call_tool, lambda: "token")

        assert result.args_schema is not None
