"""Unit tests for the mcp 1.x/2.x compatibility shims."""

from types import SimpleNamespace

from sap_cloud_sdk.agentgateway._compat import (
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
