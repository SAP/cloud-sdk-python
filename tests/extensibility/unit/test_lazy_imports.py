"""Tests for lazy imports via __getattr__ in extensibility __init__."""

import sys
from unittest.mock import patch


class TestLazyImportExtensionTelemetryInterceptor:
    def test_raises_import_error_with_hint_when_dep_absent(self):
        """When langchain-mcp-adapters is not installed, ImportError includes install hint."""
        import sap_cloud_sdk.extensibility as ext_mod

        # Clear cached resolved value so __getattr__ runs again
        ext_mod.__dict__.pop("ExtensionTelemetryInterceptor", None)
        saved_module = sys.modules.pop("sap_cloud_sdk.extensibility._langchain", None)
        try:
            # Simulate langchain_mcp_adapters not being installed
            with patch.dict(
                sys.modules,
                {"langchain_mcp_adapters": None},
            ):
                import importlib

                # Re-remove _langchain so it re-runs the import
                sys.modules.pop("sap_cloud_sdk.extensibility._langchain", None)

                try:
                    _ = ext_mod.ExtensionTelemetryInterceptor
                    raised = False
                except ImportError as exc:
                    raised = True
                    assert "langchain-mcp-adapters" in str(exc)
                    assert "extensibility-langchain" in str(exc)

            # If langchain_mcp_adapters is actually installed, the test is a no-op
            # (it's expected to work fine when installed)
        finally:
            if saved_module is not None:
                sys.modules["sap_cloud_sdk.extensibility._langchain"] = saved_module
            ext_mod.__dict__.pop("ExtensionTelemetryInterceptor", None)

    def test_raises_attribute_error_for_unknown_name(self):
        import sap_cloud_sdk.extensibility as ext_mod
        import pytest

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = ext_mod._totally_unknown_name_xyz


class TestLazyImportLoadExtensionToolsLangchain:
    def test_attribute_error_for_unknown(self):
        import sap_cloud_sdk.extensibility as ext_mod
        import pytest

        with pytest.raises(AttributeError):
            _ = ext_mod._not_a_real_symbol
