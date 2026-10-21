"""Unit tests for the mcp 1.x/2.x compatibility shims."""

from types import SimpleNamespace

from sap_cloud_sdk.agentgateway._compat import (
    find_malformed_result_error,
    find_mcp_error,
    make_mcp_error,
    mcp_input_schema,
    mcp_is_error,
    mcp_server_name,
)


class TestMcpServerName:
    """Tests for mcp_server_name across both mcp majors."""

    def test_reads_snake_case_server_info_mcp_2x(self):
        """mcp 2.x exposes ``server_info`` (snake_case)."""
        init = SimpleNamespace(server_info=SimpleNamespace(name="srv-2x"))
        assert mcp_server_name(init) == "srv-2x"

    def test_reads_camel_case_server_info_mcp_1x(self):
        """mcp 1.x exposes ``serverInfo`` (camelCase)."""
        init = SimpleNamespace(serverInfo=SimpleNamespace(name="srv-1x"))
        assert mcp_server_name(init) == "srv-1x"

    def test_returns_none_when_server_info_missing(self):
        """No server info field on either name -> None."""
        assert mcp_server_name(SimpleNamespace()) is None

    def test_returns_none_when_name_missing(self):
        """server_info present but without a ``name`` -> None."""
        init = SimpleNamespace(server_info=SimpleNamespace())
        assert mcp_server_name(init) is None

    def test_returns_none_when_init_result_is_none(self):
        """A falsy init_result must not raise -> None."""
        assert mcp_server_name(None) is None

    def test_works_against_real_installed_mcp_types(self):
        """Prove it works against the actually-installed mcp library."""
        from mcp.types import Implementation, InitializeResult

        init = InitializeResult(
            protocolVersion="2025-06-18",
            capabilities={},
            serverInfo=Implementation(name="real-srv", version="1.0.0"),
        )
        assert mcp_server_name(init) == "real-srv"


class TestMcpInputSchema:
    """Tests for mcp_input_schema across both mcp majors."""

    def test_reads_snake_case_input_schema_mcp_2x(self):
        """mcp 2.x exposes ``input_schema`` (snake_case)."""
        tool = SimpleNamespace(input_schema={"type": "object"})
        assert mcp_input_schema(tool) == {"type": "object"}

    def test_reads_camel_case_input_schema_mcp_1x(self):
        """mcp 1.x exposes ``inputSchema`` (camelCase)."""
        tool = SimpleNamespace(inputSchema={"type": "string"})
        assert mcp_input_schema(tool) == {"type": "string"}

    def test_defaults_to_empty_dict_when_missing(self):
        """No schema field on either name -> {}."""
        assert mcp_input_schema(SimpleNamespace()) == {}

    def test_defaults_to_empty_dict_when_none(self):
        """Schema explicitly None -> {}."""
        assert mcp_input_schema(SimpleNamespace(input_schema=None)) == {}


class TestMcpIsError:
    """Tests for mcp_is_error across both mcp majors."""

    def test_reads_snake_case_is_error_mcp_2x(self):
        """mcp 2.x exposes ``is_error`` (snake_case)."""
        assert mcp_is_error(SimpleNamespace(is_error=True)) is True

    def test_reads_camel_case_is_error_mcp_1x(self):
        """mcp 1.x exposes ``isError`` (camelCase)."""
        assert mcp_is_error(SimpleNamespace(isError=True)) is True

    def test_false_when_flag_false(self):
        """An explicit False flag stays False."""
        assert mcp_is_error(SimpleNamespace(is_error=False)) is False

    def test_defaults_to_false_when_missing(self):
        """No error field on either name -> False."""
        assert mcp_is_error(SimpleNamespace()) is False


class TestFindMcpError:
    """Tests for find_mcp_error unwrapping."""

    def test_returns_bare_mcp_error(self):
        """A bare McpError is returned directly."""
        err = make_mcp_error(-32602, "Unknown tool: foo")
        assert find_mcp_error(err) is err

    def test_finds_mcp_error_in_group(self):
        """An McpError wrapped in a BaseExceptionGroup is found."""
        err = make_mcp_error(-32603, "Internal Server Error")
        group = BaseExceptionGroup("eg", [err])
        assert find_mcp_error(group) is err

    def test_finds_mcp_error_in_nested_group(self):
        """An McpError nested in a group within a group is found."""
        err = make_mcp_error(-32600, "bad request")
        group = BaseExceptionGroup("outer", [BaseExceptionGroup("inner", [err])])
        assert find_mcp_error(group) is err

    def test_returns_none_without_mcp_error(self):
        """A group without any McpError leaf returns None (defer to generic handling)."""
        group = BaseExceptionGroup("eg", [ValueError("x"), RuntimeError("y")])
        assert find_mcp_error(group) is None

    def test_returns_none_for_unrelated_exception(self):
        """A plain non-group, non-McpError exception returns None."""
        assert find_mcp_error(ValueError("x")) is None


class TestFindMalformedResultError:
    """Tests for find_malformed_result_error — the isError/is_error-on-None crash."""

    def test_returns_bare_isError_attributeerror(self):
        """The mcp 1.x deref: AttributeError mentioning 'isError' is recognised."""
        err = AttributeError("'NoneType' object has no attribute 'isError'")
        assert find_malformed_result_error(err) is err

    def test_returns_bare_is_error_attributeerror(self):
        """The mcp 2.x deref: AttributeError mentioning 'is_error' is recognised."""
        err = AttributeError("'NoneType' object has no attribute 'is_error'")
        assert find_malformed_result_error(err) is err

    def test_finds_attributeerror_in_group(self):
        """Wrapped in a BaseExceptionGroup (anyio task group), it is still found."""
        err = AttributeError("'NoneType' object has no attribute 'isError'")
        group = BaseExceptionGroup("eg", [err])
        assert find_malformed_result_error(group) is err

    def test_finds_attributeerror_in_nested_group(self):
        """Found through nested BaseExceptionGroups."""
        err = AttributeError("'NoneType' object has no attribute 'isError'")
        group = BaseExceptionGroup("outer", [BaseExceptionGroup("inner", [err])])
        assert find_malformed_result_error(group) is err

    def test_returns_none_for_unrelated_attributeerror(self):
        """An AttributeError not about isError/is_error is NOT matched (not masked)."""
        assert find_malformed_result_error(AttributeError("no attr 'bar'")) is None

    def test_returns_none_for_unrelated_exception(self):
        """A non-AttributeError exception returns None."""
        assert find_malformed_result_error(ValueError("x")) is None

    def test_returns_none_without_match_in_group(self):
        """A group with no matching AttributeError leaf returns None."""
        group = BaseExceptionGroup("eg", [ValueError("x"), RuntimeError("y")])
        assert find_malformed_result_error(group) is None
