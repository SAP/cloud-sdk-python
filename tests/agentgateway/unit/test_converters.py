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


class TestMcpToolToLangchainTypeMapping:
    """Tests that JSON Schema types are mapped to the correct Python types."""

    def _tool_with_types(self, properties: dict, required: list[str] | None = None) -> MCPTool:
        return MCPTool(
            name="typed_tool",
            server_name="server",
            description="desc",
            input_schema={
                "type": "object",
                "required": required or [],
                "properties": properties,
            },
            url="https://example.com/mcp",
        )

    def test_string_type_maps_to_str(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"name": {"type": "string"}}, required=["name"]),
            AsyncMock(),
            lambda: "token",
        )
        assert _schema_fields(lc_tool)["name"].annotation is str

    def test_integer_type_maps_to_int(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"limit": {"type": "integer"}}, required=["limit"]),
            AsyncMock(),
            lambda: "token",
        )
        assert _schema_fields(lc_tool)["limit"].annotation is int

    def test_number_type_maps_to_float(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"ratio": {"type": "number"}}, required=["ratio"]),
            AsyncMock(),
            lambda: "token",
        )
        assert _schema_fields(lc_tool)["ratio"].annotation is float

    def test_boolean_type_maps_to_bool(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"active": {"type": "boolean"}}, required=["active"]),
            AsyncMock(),
            lambda: "token",
        )
        assert _schema_fields(lc_tool)["active"].annotation is bool

    def test_array_type_maps_to_list(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"tags": {"type": "array"}}, required=["tags"]),
            AsyncMock(),
            lambda: "token",
        )
        assert _schema_fields(lc_tool)["tags"].annotation is list

    def test_object_type_maps_to_dict(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"meta": {"type": "object"}}, required=["meta"]),
            AsyncMock(),
            lambda: "token",
        )
        assert _schema_fields(lc_tool)["meta"].annotation is dict

    def test_unknown_type_maps_to_any(self):
        from typing import Any
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"data": {"type": "unknown"}}, required=["data"]),
            AsyncMock(),
            lambda: "token",
        )
        assert _schema_fields(lc_tool)["data"].annotation is Any

    def test_missing_type_maps_to_any(self):
        from typing import Any
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"data": {}}, required=["data"]),
            AsyncMock(),
            lambda: "token",
        )
        assert _schema_fields(lc_tool)["data"].annotation is Any

    def test_optional_non_string_field_is_nullable(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"limit": {"type": "integer"}}),
            AsyncMock(),
            lambda: "token",
        )
        field = _schema_fields(lc_tool)["limit"]
        assert not field.is_required()
        # annotation should be int | None
        import types as _types
        assert isinstance(field.annotation, _types.UnionType)
        assert int in field.annotation.__args__
        assert type(None) in field.annotation.__args__

    def test_array_type_integer_null_maps_to_int(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"limit": {"type": ["integer", "null"]}}, required=["limit"]),
            AsyncMock(),
            lambda: "token",
        )
        field = _schema_fields(lc_tool)["limit"]
        import types as _types
        assert isinstance(field.annotation, _types.UnionType)
        assert int in field.annotation.__args__
        assert type(None) in field.annotation.__args__

    def test_array_type_number_null_maps_to_float(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"ratio": {"type": ["number", "null"]}}, required=["ratio"]),
            AsyncMock(),
            lambda: "token",
        )
        field = _schema_fields(lc_tool)["ratio"]
        import types as _types
        assert isinstance(field.annotation, _types.UnionType)
        assert float in field.annotation.__args__
        assert type(None) in field.annotation.__args__

    def test_array_type_multiple_scalars_uses_first_non_null(self):
        # e.g. {"type": ["number", "string", "null"]} — pick "number"
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"val": {"type": ["number", "string", "null"]}}, required=["val"]),
            AsyncMock(),
            lambda: "token",
        )
        field = _schema_fields(lc_tool)["val"]
        import types as _types
        assert isinstance(field.annotation, _types.UnionType)
        assert float in field.annotation.__args__
        assert type(None) in field.annotation.__args__

    def test_array_type_without_null_is_not_nullable(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_types({"count": {"type": ["integer"]}}, required=["count"]),
            AsyncMock(),
            lambda: "token",
        )
        field = _schema_fields(lc_tool)["count"]
        assert field.annotation is int


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
