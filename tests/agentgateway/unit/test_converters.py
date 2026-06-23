"""Unit tests for MCP tool converters."""

import pytest
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

        assert result.name == "create_order"
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

        assert result.name == "simple_tool"
        assert result.args_schema is not None

    def test_optional_fields_not_required_in_args_schema(self):
        """Fields absent from 'required' must be optional in the generated Pydantic model."""
        tool = MCPTool(
            name="get_supplier_bid",
            server_name="ariba",
            description="Gets all supplier bids for the specified event",
            input_schema={
                "type": "object",
                "required": ["eventid"],
                "properties": {
                    "eventid": {"description": "Unique identifier of the event"},
                    "showdeclinedreason": {"description": "Show supplier decline reason"},
                    "datafetchmode": {"description": "Level of detail for the response"},
                },
            },
            url="https://example.com/mcp",
        )

        result = mcp_tool_to_langchain(tool, AsyncMock(return_value="result"), lambda: "token")

        from pydantic import BaseModel

        assert result.args_schema is not None and isinstance(result.args_schema, type) and issubclass(result.args_schema, BaseModel)
        fields = result.args_schema.model_fields
        assert fields["eventid"].is_required(), "eventid should be required"
        assert not fields["showdeclinedreason"].is_required(), "showdeclinedreason should be optional"
        assert not fields["datafetchmode"].is_required(), "datafetchmode should be optional"

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


class TestMcpToolToLangchainInvocation:
    """End-to-end invocation tests for mcp_tool_to_langchain."""

    @pytest.mark.asyncio
    async def test_required_param_forwarded(self):
        """Required parameters are forwarded to call_tool."""
        tool = MCPTool(
            name="get_supplier_bid",
            server_name="ariba",
            description="Gets supplier bids",
            input_schema={
                "type": "object",
                "required": ["eventid"],
                "properties": {
                    "eventid": {"type": "string"},
                    "showdeclinedreason": {"type": "string"},
                },
            },
            url="https://example.com/mcp",
        )
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(tool, call_tool, lambda: "token")

        await lc_tool.arun({"eventid": "E001"})

        call_tool.assert_awaited_once()
        kwargs = call_tool.call_args.kwargs
        assert kwargs["eventid"] == "E001"

    @pytest.mark.asyncio
    async def test_optional_params_omitted_when_not_supplied(self):
        """Optional parameters not supplied by the LLM must not be forwarded as None."""
        tool = MCPTool(
            name="get_supplier_bid",
            server_name="ariba",
            description="Gets supplier bids",
            input_schema={
                "type": "object",
                "required": ["eventid"],
                "properties": {
                    "eventid": {"type": "string"},
                    "showdeclinedreason": {"type": "string"},
                    "datafetchmode": {"type": "string"},
                },
            },
            url="https://example.com/mcp",
        )
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(tool, call_tool, lambda: "token")

        await lc_tool.arun({"eventid": "E001"})

        kwargs = call_tool.call_args.kwargs
        assert "showdeclinedreason" not in kwargs
        assert "datafetchmode" not in kwargs

    @pytest.mark.asyncio
    async def test_optional_param_forwarded_when_supplied(self):
        """Optional parameters that the LLM does supply are forwarded."""
        tool = MCPTool(
            name="get_supplier_bid",
            server_name="ariba",
            description="Gets supplier bids",
            input_schema={
                "type": "object",
                "required": ["eventid"],
                "properties": {
                    "eventid": {"type": "string"},
                    "showdeclinedreason": {"type": "string"},
                },
            },
            url="https://example.com/mcp",
        )
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(tool, call_tool, lambda: "token")

        await lc_tool.arun({"eventid": "E001", "showdeclinedreason": "true"})

        kwargs = call_tool.call_args.kwargs
        assert kwargs["showdeclinedreason"] == "true"
