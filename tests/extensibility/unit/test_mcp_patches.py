"""Tests for unwrap_buggy_mcp_otel_patches."""

import sys
from unittest.mock import MagicMock, patch

from sap_cloud_sdk.extensibility._mcp_patches import unwrap_buggy_mcp_otel_patches


class TestUnwrapBuggyMcpOtelPatches:
    def test_no_op_when_otel_instrumentation_absent(self):
        """Should silently succeed when opentelemetry.instrumentation is not importable."""
        with patch.dict(sys.modules, {"opentelemetry.instrumentation.utils": None}):
            unwrap_buggy_mcp_otel_patches()

    def test_no_op_on_any_exception(self):
        """Should swallow any exception, never raise."""
        with patch(
            "sap_cloud_sdk.extensibility._mcp_patches.unwrap_buggy_mcp_otel_patches"
        ):
            pass
        import builtins

        real_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if "opentelemetry.instrumentation.utils" in name:
                raise RuntimeError("unexpected")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            unwrap_buggy_mcp_otel_patches()

    def test_calls_unwrap_when_present(self):
        mock_unwrap = MagicMock()
        mock_utils = MagicMock()
        mock_utils.unwrap = mock_unwrap

        mock_mcp_session = MagicMock()
        mock_streamable_http = MagicMock()
        mock_langchain_sessions = MagicMock()

        with patch.dict(
            sys.modules,
            {
                "opentelemetry.instrumentation.utils": mock_utils,
                "mcp.shared.session": mock_mcp_session,
                "mcp.client.streamable_http": mock_streamable_http,
                "langchain_mcp_adapters.sessions": mock_langchain_sessions,
                "mcp": MagicMock(),
                "mcp.client": MagicMock(),
            },
        ):
            unwrap_buggy_mcp_otel_patches()
            assert mock_unwrap.called
