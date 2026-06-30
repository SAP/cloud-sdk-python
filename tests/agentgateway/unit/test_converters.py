"""Unit tests for MCP tool converters."""

import pytest
from unittest.mock import AsyncMock
from pydantic import BaseModel

from sap_cloud_sdk.agentgateway import MCPTool
from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain


def _schema_fields(lc_tool):
    """Narrow args_schema to BaseModel and return model_fields."""
    schema = lc_tool.args_schema
    assert isinstance(schema, type) and issubclass(schema, BaseModel)
    return schema.model_fields


def _make_tool(*, required=("eventid",), optional=("showdeclinedreason", "datafetchmode")):
    properties = {k: {"type": "string"} for k in (*required, *optional)}
    return MCPTool(
        name="get_supplier_bid",
        server_name="ariba",
        description="Gets all supplier bids for the specified event",
        input_schema={"type": "object", "required": list(required), "properties": properties},
        url="https://example.com/mcp",
    )


class TestMcpToolToLangchainStructure:
    """Tests that the converter produces a correctly structured LangChain StructuredTool."""

    def test_tool_metadata_matches_mcp_tool(self):
        """name, description, and coroutine are taken from the MCPTool."""
        lc_tool = mcp_tool_to_langchain(_make_tool(), AsyncMock(return_value="ok"), lambda: "token")

        assert lc_tool.name == "get_supplier_bid"
        assert lc_tool.description == "Gets all supplier bids for the specified event"
        assert lc_tool.coroutine is not None

    def test_args_schema_is_pydantic_model_with_all_properties(self):
        """args_schema is a Pydantic BaseModel that includes every property from input_schema."""
        lc_tool = mcp_tool_to_langchain(_make_tool(), AsyncMock(return_value="ok"), lambda: "token")

        assert lc_tool.args_schema is not None
        fields = _schema_fields(lc_tool)
        assert "eventid" in fields
        assert "showdeclinedreason" in fields
        assert "datafetchmode" in fields

    def test_required_fields_are_required_in_args_schema(self):
        """Fields listed in 'required' must be required in the Pydantic model."""
        lc_tool = mcp_tool_to_langchain(_make_tool(), AsyncMock(return_value="ok"), lambda: "token")

        assert _schema_fields(lc_tool)["eventid"].is_required()

    def test_optional_fields_are_not_required_in_args_schema(self):
        """Fields absent from 'required' must be optional in the Pydantic model."""
        lc_tool = mcp_tool_to_langchain(_make_tool(), AsyncMock(return_value="ok"), lambda: "token")

        fields = _schema_fields(lc_tool)
        assert not fields["showdeclinedreason"].is_required()
        assert not fields["datafetchmode"].is_required()

    def test_empty_input_schema_produces_valid_tool(self):
        """MCPTool with no properties at all still produces a usable StructuredTool."""
        tool = MCPTool(
            name="simple_tool",
            server_name="server",
            description="No params",
            input_schema={},
            url="https://example.com/mcp",
        )
        lc_tool = mcp_tool_to_langchain(tool, AsyncMock(return_value="ok"), lambda: "token")

        assert lc_tool.name == "simple_tool"
        assert lc_tool.args_schema is not None

    def test_input_schema_without_properties_key(self):
        """MCPTool with a type-only schema (no 'properties' key) produces a valid tool."""
        tool = MCPTool(
            name="typed_tool",
            server_name="server",
            description="Type only",
            input_schema={"type": "object"},
            url="https://example.com/mcp",
        )
        lc_tool = mcp_tool_to_langchain(tool, AsyncMock(return_value="ok"), lambda: "token")

        assert lc_tool.args_schema is not None


class TestMcpToolToLangchainInvocation:
    """End-to-end invocation tests: verify what actually reaches call_tool."""

    @pytest.mark.asyncio
    async def test_required_param_forwarded(self):
        """Required parameters supplied by the LLM are forwarded to call_tool."""
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(_make_tool(), call_tool, lambda: "token")

        await lc_tool.arun({"eventid": "E001"})

        call_tool.assert_awaited_once()
        assert call_tool.call_args.kwargs["eventid"] == "E001"

    @pytest.mark.asyncio
    async def test_optional_params_omitted_when_not_supplied(self):
        """Optional parameters absent from the LLM response must not reach call_tool as None."""
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(_make_tool(), call_tool, lambda: "token")

        await lc_tool.arun({"eventid": "E001"})

        kwargs = call_tool.call_args.kwargs
        assert "showdeclinedreason" not in kwargs
        assert "datafetchmode" not in kwargs

    @pytest.mark.asyncio
    async def test_optional_params_omitted_when_llm_sends_none(self):
        """Optional parameters explicitly set to None by the LLM must not reach call_tool."""
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(_make_tool(), call_tool, lambda: "token")

        await lc_tool.arun({"eventid": "E001", "showdeclinedreason": None, "datafetchmode": None})

        kwargs = call_tool.call_args.kwargs
        assert "showdeclinedreason" not in kwargs
        assert "datafetchmode" not in kwargs

    @pytest.mark.asyncio
    async def test_optional_param_forwarded_when_supplied(self):
        """Optional parameters with a real value supplied by the LLM are forwarded."""
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(_make_tool(), call_tool, lambda: "token")

        await lc_tool.arun({"eventid": "E001", "showdeclinedreason": "true"})

        assert call_tool.call_args.kwargs["showdeclinedreason"] == "true"

    @pytest.mark.asyncio
    async def test_none_values_forwarded_when_omit_none_false(self):
        """When omit_none=False, None values are forwarded to call_tool as-is."""
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(_make_tool(), call_tool, lambda: "token", omit_none=False)

        await lc_tool.arun({"eventid": "E001", "showdeclinedreason": None})

        kwargs = call_tool.call_args.kwargs
        assert "showdeclinedreason" in kwargs
        assert kwargs["showdeclinedreason"] is None
