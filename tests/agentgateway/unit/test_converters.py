"""Unit tests for MCP tool converters."""

import pytest
from unittest.mock import AsyncMock
from pydantic import BaseModel

from sap_cloud_sdk.agentgateway import MCPTool
from sap_cloud_sdk.agentgateway.converters import mcp_tool_to_langchain


def _schema_fields(lc_tool):
    """Return model_fields from the args_schema Pydantic model."""
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
            self._tool_with_types(
                {"val": {"type": ["number", "string", "null"]}}, required=["val"]
            ),
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


class TestMcpToolToLangchainUnderscoredParams:
    """OData CSDL §15.2 allows '_'-prefixed identifiers; Pydantic v2 rejects them.

    The converter strips leading underscores for the Pydantic model and restores
    originals before forwarding to call_tool via an internal name_map.
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

    def test_underscored_required_param_present_in_schema(self):
        """'_VariantConfiguration' must appear in the args schema (stripped to safe name)."""
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_underscore_params(), AsyncMock(return_value="ok"), lambda: "token"
        )
        fields = _schema_fields(lc_tool)
        assert "VariantConfiguration" in fields
        assert fields["VariantConfiguration"].is_required()

    def test_underscored_optional_param_present_in_schema(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_underscore_params(), AsyncMock(return_value="ok"), lambda: "token"
        )
        fields = _schema_fields(lc_tool)
        assert "Product" in fields
        assert not fields["Product"].is_required()

    def test_non_underscored_param_unaffected(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_underscore_params(), AsyncMock(return_value="ok"), lambda: "token"
        )
        assert "NormalParam" in _schema_fields(lc_tool)

    @pytest.mark.asyncio
    async def test_original_underscore_name_restored_on_invocation(self):
        """call_tool must receive '_VariantConfiguration', not 'VariantConfiguration'."""
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_underscore_params(), call_tool, lambda: "token"
        )

        await lc_tool.arun({"VariantConfiguration": "VC001"})

        kwargs = call_tool.call_args.kwargs
        assert "_VariantConfiguration" in kwargs
        assert kwargs["_VariantConfiguration"] == "VC001"
        assert "VariantConfiguration" not in kwargs

    @pytest.mark.asyncio
    async def test_optional_underscore_param_restored_when_supplied(self):
        call_tool = AsyncMock(return_value="ok")
        lc_tool = mcp_tool_to_langchain(
            self._tool_with_underscore_params(), call_tool, lambda: "token"
        )

        await lc_tool.arun({"VariantConfiguration": "VC001", "Product": "P001"})

        kwargs = call_tool.call_args.kwargs
        assert kwargs.get("_Product") == "P001"
        assert "Product" not in kwargs


class TestMcpToolToLangchainFieldMetadata:
    """JSON Schema property metadata is forwarded to Pydantic Field.

    Fields with a native Pydantic equivalent go there directly; everything
    else is preserved via json_schema_extra so the LLM still sees them.
    """

    def _tool(self, properties: dict, required: list[str] | None = None) -> MCPTool:
        return MCPTool(
            name="meta_tool",
            server_name="server",
            description="desc",
            input_schema={
                "type": "object",
                "required": required or [],
                "properties": properties,
            },
            url="https://example.com/mcp",
        )

    # --- native Field kwargs ---

    def test_description_preserved_on_required_field(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"s": {"type": "string", "description": "The status"}}, required=["s"]),
            AsyncMock(), lambda: "token",
        )
        assert _schema_fields(lc_tool)["s"].description == "The status"

    def test_description_preserved_on_optional_field(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"s": {"type": "string", "description": "The status"}}),
            AsyncMock(), lambda: "token",
        )
        assert _schema_fields(lc_tool)["s"].description == "The status"

    def test_title_preserved(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"n": {"type": "string", "title": "OriginalName"}}, required=["n"]),
            AsyncMock(), lambda: "token",
        )
        assert _schema_fields(lc_tool)["n"].title == "OriginalName"

    def test_examples_preserved_as_native_field_kwarg(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"n": {"type": "string", "examples": ["Alice", "Bob"]}}, required=["n"]),
            AsyncMock(), lambda: "token",
        )
        assert _schema_fields(lc_tool)["n"].examples == ["Alice", "Bob"]

    def test_deprecated_preserved(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"n": {"type": "string", "deprecated": True}}, required=["n"]),
            AsyncMock(), lambda: "token",
        )
        assert _schema_fields(lc_tool)["n"].deprecated is True

    def test_pattern_preserved(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"n": {"type": "string", "pattern": "^[a-z]+$"}}, required=["n"]),
            AsyncMock(), lambda: "token",
        )
        assert _schema_fields(lc_tool)["n"].metadata  # pattern lives in metadata

    def test_min_max_length_preserved(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"n": {"type": "string", "minLength": 2, "maxLength": 50}}, required=["n"]),
            AsyncMock(), lambda: "token",
        )
        schema = lc_tool.args_schema.model_json_schema()
        assert schema["properties"]["n"]["minLength"] == 2
        assert schema["properties"]["n"]["maxLength"] == 50

    def test_minimum_maximum_preserved(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"v": {"type": "integer", "minimum": 1, "maximum": 100}}, required=["v"]),
            AsyncMock(), lambda: "token",
        )
        schema = lc_tool.args_schema.model_json_schema()
        assert schema["properties"]["v"]["minimum"] == 1
        assert schema["properties"]["v"]["maximum"] == 100

    # --- json_schema_extra bucket ---

    def test_enum_preserved_in_json_schema_extra(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"c": {"type": "string", "enum": ["red", "green", "blue"]}}, required=["c"]),
            AsyncMock(), lambda: "token",
        )
        schema = lc_tool.args_schema.model_json_schema()
        assert schema["properties"]["c"]["enum"] == ["red", "green", "blue"]

    def test_default_preserved_in_json_schema_extra(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"c": {"type": "string", "default": "active"}}, required=["c"]),
            AsyncMock(), lambda: "token",
        )
        schema = lc_tool.args_schema.model_json_schema()
        assert schema["properties"]["c"]["default"] == "active"

    def test_example_preserved_in_json_schema_extra(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"c": {"type": "string", "example": "hello"}}, required=["c"]),
            AsyncMock(), lambda: "token",
        )
        schema = lc_tool.args_schema.model_json_schema()
        assert schema["properties"]["c"]["example"] == "hello"

    def test_format_preserved_in_json_schema_extra(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"ts": {"type": "string", "format": "date-time"}}, required=["ts"]),
            AsyncMock(), lambda: "token",
        )
        schema = lc_tool.args_schema.model_json_schema()
        assert schema["properties"]["ts"]["format"] == "date-time"

    def test_const_preserved_in_json_schema_extra(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"v": {"type": "string", "const": "fixed"}}, required=["v"]),
            AsyncMock(), lambda: "token",
        )
        schema = lc_tool.args_schema.model_json_schema()
        assert schema["properties"]["v"]["const"] == "fixed"

    def test_multiple_extra_keys_coexist(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool(
                {"s": {"type": "string", "enum": ["a", "b"], "format": "uuid", "example": "a"}},
                required=["s"],
            ),
            AsyncMock(), lambda: "token",
        )
        schema = lc_tool.args_schema.model_json_schema()
        assert schema["properties"]["s"]["enum"] == ["a", "b"]
        assert schema["properties"]["s"]["format"] == "uuid"
        assert schema["properties"]["s"]["example"] == "a"

    def test_missing_metadata_produces_no_extra(self):
        lc_tool = mcp_tool_to_langchain(
            self._tool({"id": {"type": "string"}}, required=["id"]),
            AsyncMock(), lambda: "token",
        )
        field = _schema_fields(lc_tool)["id"]
        assert field.description is None
        assert field.json_schema_extra is None

    def test_unknown_keys_are_silently_ignored(self):
        """Keys not in either bucket (e.g. future JSON Schema extensions) must not raise."""
        lc_tool = mcp_tool_to_langchain(
            self._tool({"x": {"type": "string", "x-custom-ext": "value"}}, required=["x"]),
            AsyncMock(), lambda: "token",
        )
        assert "x" in _schema_fields(lc_tool)


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
