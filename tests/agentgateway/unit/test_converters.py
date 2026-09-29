"""Unit tests for MCP tool converters."""

import pytest
from unittest.mock import AsyncMock

from sap_cloud_sdk.agentgateway import MCPTool
from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain


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

    def test_args_schema_is_the_input_schema_dict(self):
        """args_schema must be the raw JSON Schema dict from the MCPTool."""
        tool = _make_tool()
        lc_tool = mcp_tool_to_langchain(tool, AsyncMock(return_value="ok"), lambda: "token")

        assert lc_tool.args_schema is tool.input_schema

    def test_args_schema_preserves_all_properties(self):
        """All property names from input_schema survive in args_schema unchanged."""
        lc_tool = mcp_tool_to_langchain(_make_tool(), AsyncMock(return_value="ok"), lambda: "token")

        props = lc_tool.args_schema["properties"]
        assert "eventid" in props
        assert "showdeclinedreason" in props
        assert "datafetchmode" in props

    def test_args_schema_preserves_required(self):
        """The 'required' list is preserved verbatim in args_schema."""
        lc_tool = mcp_tool_to_langchain(_make_tool(), AsyncMock(return_value="ok"), lambda: "token")

        assert "eventid" in lc_tool.args_schema["required"]

    def test_empty_input_schema_produces_valid_tool(self):
        """MCPTool with no properties still produces a usable StructuredTool."""
        tool = MCPTool(
            name="simple_tool",
            server_name="server",
            description="No params",
            input_schema={},
            url="https://example.com/mcp",
        )
        lc_tool = mcp_tool_to_langchain(tool, AsyncMock(return_value="ok"), lambda: "token")

        assert lc_tool.name == "simple_tool"

    def test_input_schema_without_properties_key_produces_valid_tool(self):
        """MCPTool with a type-only schema (no 'properties' key) still produces a usable tool."""
        tool = MCPTool(
            name="typed_tool",
            server_name="server",
            description="Type only",
            input_schema={"type": "object"},
            url="https://example.com/mcp",
        )
        lc_tool = mcp_tool_to_langchain(tool, AsyncMock(return_value="ok"), lambda: "token")

        assert lc_tool.name == "typed_tool"


class TestMcpToolToLangchainUnderscoredParams:
    """OData CSDL §15.2 allows '_'-prefixed identifiers.

    With a dict-based args_schema, Pydantic's private-attribute convention is
    bypassed entirely — underscore names reach the LLM and call_tool unchanged.
    """

    def _tool_with_underscore_params(self):
        return MCPTool(
            name="get_variant_config",
            server_name="s4hana",
            description="Get variant configuration",
            input_schema={
                "type": "object",
                "required": ["_VariantConfiguration"],
                "properties": {
                    "_VariantConfiguration": {"type": "string"},
                    "_Product": {"type": "string"},
                    "NormalParam": {"type": "string"},
                },
            },
            url="https://example.com/mcp",
        )

    def test_underscored_params_present_in_schema_unchanged(self):
        """'_VariantConfiguration' and '_Product' must appear as-is in args_schema."""
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_underscore_params(), AsyncMock(return_value="ok"), lambda: "token"
        )
        props = lc_tool.args_schema["properties"]
        assert "_VariantConfiguration" in props
        assert "_Product" in props

    def test_underscored_required_param_in_required_list(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_underscore_params(), AsyncMock(return_value="ok"), lambda: "token"
        )
        assert "_VariantConfiguration" in lc_tool.args_schema["required"]

    def test_non_underscored_param_unaffected(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_underscore_params(), AsyncMock(return_value="ok"), lambda: "token"
        )
        assert "NormalParam" in lc_tool.args_schema["properties"]

    @pytest.mark.asyncio
    async def test_underscored_param_forwarded_to_call_tool_unchanged(self):
        """call_tool must receive '_VariantConfiguration' exactly as the LLM supplied it."""
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_underscore_params(), call_tool, lambda: "token"
        )

        await lc_tool.arun({"_VariantConfiguration": "VC001"})

        kwargs = call_tool.call_args.kwargs
        assert kwargs["_VariantConfiguration"] == "VC001"


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
