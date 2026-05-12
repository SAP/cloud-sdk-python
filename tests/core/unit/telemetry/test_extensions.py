"""Tests for extension telemetry utilities."""

import asyncio
import logging
import pytest
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

from sap_cloud_sdk.core.telemetry.extensions import (
    extension_context,
    get_extension_context,
    ExtensionType,
    ATTR_IS_EXTENSION,
    ATTR_EXTENSION_TYPE,
    ATTR_CAPABILITY_ID,
    ATTR_EXTENSION_ID,
    ATTR_EXTENSION_NAME,
    ATTR_EXTENSION_VERSION,
    ATTR_EXTENSION_ITEM_NAME,
    ATTR_EXTENSION_URL,
    ATTR_SOLUTION_ID,
    ATTR_SUMMARY_TOTAL_OPERATION_COUNT,
    ATTR_SUMMARY_TOTAL_DURATION_MS,
    ATTR_SUMMARY_TOOL_CALL_COUNT,
    ATTR_SUMMARY_HOOK_CALL_COUNT,
    ATTR_SUMMARY_HAS_INSTRUCTION,
    resolve_source_info,
    build_extension_span_attributes,
    reset_tool_call_metrics,
    get_tool_call_metrics,
    record_tool_call_duration,
    reset_hook_call_metrics,
    get_hook_call_metrics,
    record_hook_call_duration,
    call_extension_tool,
    call_extension_hook,
    emit_extensions_summary_span,
    ExtensionContextLogFilter,
)


class TestExtensionType:
    """Test suite for ExtensionType enum."""

    def test_extension_type_values(self):
        """Test ExtensionType enum has correct values."""
        assert ExtensionType.TOOL.value == "tool"
        assert ExtensionType.INSTRUCTION.value == "instruction"
        assert ExtensionType.HOOK.value == "hook"

    def test_extension_type_is_string_enum(self):
        """Test ExtensionType is a string enum."""
        assert isinstance(ExtensionType.TOOL, str)
        assert ExtensionType.TOOL == "tool"

    def test_extension_type_all_values(self):
        """Test all ExtensionType values are accessible."""
        all_types = list(ExtensionType)
        assert len(all_types) == 3
        assert ExtensionType.TOOL in all_types
        assert ExtensionType.INSTRUCTION in all_types
        assert ExtensionType.HOOK in all_types


class TestAttributeKeys:
    """Test suite for attribute/baggage key constants."""

    def test_attribute_keys_are_strings(self):
        """Test attribute keys are strings."""
        assert isinstance(ATTR_IS_EXTENSION, str)
        assert isinstance(ATTR_EXTENSION_TYPE, str)
        assert isinstance(ATTR_CAPABILITY_ID, str)
        assert isinstance(ATTR_EXTENSION_ID, str)
        assert isinstance(ATTR_EXTENSION_NAME, str)
        assert isinstance(ATTR_EXTENSION_VERSION, str)
        assert isinstance(ATTR_EXTENSION_ITEM_NAME, str)

    def test_attribute_keys_have_sap_extension_prefix(self):
        """Test attribute keys have sap.extension. prefix."""
        assert ATTR_IS_EXTENSION.startswith("sap.extension.")
        assert ATTR_EXTENSION_TYPE.startswith("sap.extension.")
        assert ATTR_CAPABILITY_ID.startswith("sap.extension.")
        assert ATTR_EXTENSION_ID.startswith("sap.extension.")
        assert ATTR_EXTENSION_NAME.startswith("sap.extension.")
        assert ATTR_EXTENSION_VERSION.startswith("sap.extension.")
        assert ATTR_EXTENSION_ITEM_NAME.startswith("sap.extension.")

    def test_attribute_keys_values(self):
        """Test attribute keys have expected values."""
        assert ATTR_IS_EXTENSION == "sap.extension.isExtension"
        assert ATTR_EXTENSION_TYPE == "sap.extension.extensionType"
        assert ATTR_CAPABILITY_ID == "sap.extension.capabilityId"
        assert ATTR_EXTENSION_ID == "sap.extension.extensionId"
        assert ATTR_EXTENSION_NAME == "sap.extension.extensionName"
        assert ATTR_EXTENSION_VERSION == "sap.extension.extensionVersion"
        assert ATTR_EXTENSION_ITEM_NAME == "sap.extension.extension.item.name"


class TestExtensionContext:
    """Test suite for extension_context function."""

    def test_extension_context_sets_all_baggage(self):
        """Test extension_context sets all baggage values including url and solution_id."""
        captured_baggage = {}

        def mock_set_baggage(key, value, context=None):
            captured_baggage[key] = value
            return context or MagicMock()

        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.get_current"
            ) as mock_get_current:
                with patch(
                    "sap_cloud_sdk.core.telemetry.extensions.attach"
                ) as mock_attach:
                    with patch("sap_cloud_sdk.core.telemetry.extensions.detach"):
                        mock_get_current.return_value = MagicMock()
                        mock_baggage.set_baggage = mock_set_baggage
                        mock_attach.return_value = "token"

                        with extension_context(
                            "default",
                            "ServiceNow Extension",
                            ExtensionType.TOOL,
                            extension_id="uuid-123",
                            extension_version="3",
                            item_name="create_ticket",
                            extension_url="https://ext.example.com",
                            solution_id="sol-789",
                        ):
                            pass

        assert captured_baggage[ATTR_IS_EXTENSION] == "true"
        assert captured_baggage[ATTR_EXTENSION_TYPE] == "tool"
        assert captured_baggage[ATTR_CAPABILITY_ID] == "default"
        assert captured_baggage[ATTR_EXTENSION_ID] == "uuid-123"
        assert captured_baggage[ATTR_EXTENSION_NAME] == "ServiceNow Extension"
        assert captured_baggage[ATTR_EXTENSION_VERSION] == "3"
        assert captured_baggage[ATTR_EXTENSION_ITEM_NAME] == "create_ticket"
        assert captured_baggage[ATTR_EXTENSION_URL] == "https://ext.example.com"
        assert captured_baggage[ATTR_SOLUTION_ID] == "sol-789"

    def test_extension_context_defaults_for_new_params(self):
        """Test extension_context uses defaults when new params are omitted."""
        captured_baggage = {}

        def mock_set_baggage(key, value, context=None):
            captured_baggage[key] = value
            return context or MagicMock()

        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.get_current"
            ) as mock_get_current:
                with patch(
                    "sap_cloud_sdk.core.telemetry.extensions.attach"
                ) as mock_attach:
                    with patch("sap_cloud_sdk.core.telemetry.extensions.detach"):
                        mock_get_current.return_value = MagicMock()
                        mock_baggage.set_baggage = mock_set_baggage
                        mock_attach.return_value = "token"

                        with extension_context(
                            "default",
                            "ServiceNow Extension",
                            ExtensionType.TOOL,
                        ):
                            pass

        assert captured_baggage[ATTR_IS_EXTENSION] == "true"
        assert captured_baggage[ATTR_EXTENSION_TYPE] == "tool"
        assert captured_baggage[ATTR_CAPABILITY_ID] == "default"
        assert captured_baggage[ATTR_EXTENSION_ID] == ""
        assert captured_baggage[ATTR_EXTENSION_NAME] == "ServiceNow Extension"
        assert captured_baggage[ATTR_EXTENSION_VERSION] == ""
        assert captured_baggage[ATTR_EXTENSION_ITEM_NAME] == ""
        assert ATTR_EXTENSION_URL not in captured_baggage
        assert ATTR_SOLUTION_ID not in captured_baggage

    def test_extension_context_hook_type(self):
        """Test extension_context with hook extension type."""
        captured_baggage = {}

        def mock_set_baggage(key, value, context=None):
            captured_baggage[key] = value
            return context or MagicMock()

        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.get_current"
            ) as mock_get_current:
                with patch(
                    "sap_cloud_sdk.core.telemetry.extensions.attach"
                ) as mock_attach:
                    with patch("sap_cloud_sdk.core.telemetry.extensions.detach"):
                        mock_get_current.return_value = MagicMock()
                        mock_baggage.set_baggage = mock_set_baggage
                        mock_attach.return_value = "token"

                        with extension_context(
                            "default",
                            "ap-invoice-extension",
                            ExtensionType.HOOK,
                            extension_id="uuid-hook",
                            extension_version="2",
                            item_name="Pre Invoice Hook",
                        ):
                            pass

        assert captured_baggage[ATTR_EXTENSION_TYPE] == "hook"
        assert captured_baggage[ATTR_EXTENSION_NAME] == "ap-invoice-extension"
        assert captured_baggage[ATTR_EXTENSION_ITEM_NAME] == "Pre Invoice Hook"

    def test_extension_context_attaches_and_detaches(self):
        """Test extension_context attaches and detaches context."""
        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.get_current"
            ) as mock_get_current:
                with patch(
                    "sap_cloud_sdk.core.telemetry.extensions.attach"
                ) as mock_attach:
                    with patch(
                        "sap_cloud_sdk.core.telemetry.extensions.detach"
                    ) as mock_detach:
                        mock_ctx = MagicMock()
                        mock_get_current.return_value = mock_ctx
                        mock_baggage.set_baggage.return_value = mock_ctx
                        mock_attach.return_value = "test_token"

                        with extension_context("cap", "ext_name", ExtensionType.TOOL):
                            mock_attach.assert_called_once()

                        mock_detach.assert_called_once_with("test_token")

    def test_extension_context_detaches_on_exception(self):
        """Test extension_context detaches even when exception occurs."""
        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.get_current"
            ) as mock_get_current:
                with patch(
                    "sap_cloud_sdk.core.telemetry.extensions.attach"
                ) as mock_attach:
                    with patch(
                        "sap_cloud_sdk.core.telemetry.extensions.detach"
                    ) as mock_detach:
                        mock_ctx = MagicMock()
                        mock_get_current.return_value = mock_ctx
                        mock_baggage.set_baggage.return_value = mock_ctx
                        mock_attach.return_value = "test_token"

                        with pytest.raises(ValueError, match="Test error"):
                            with extension_context(
                                "cap", "ext_name", ExtensionType.TOOL
                            ):
                                raise ValueError("Test error")

                        mock_detach.assert_called_once_with("test_token")

    def test_extension_context_propagates_exception(self):
        """Test extension_context propagates exceptions."""
        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage"):
            with patch("sap_cloud_sdk.core.telemetry.extensions.get_current"):
                with patch("sap_cloud_sdk.core.telemetry.extensions.attach"):
                    with patch("sap_cloud_sdk.core.telemetry.extensions.detach"):
                        with pytest.raises(RuntimeError, match="Test"):
                            with extension_context(
                                "cap", "ext_name", ExtensionType.TOOL
                            ):
                                raise RuntimeError("Test")

    def test_extension_context_with_different_types(self):
        """Test extension_context with different extension types."""
        for extension_type in ExtensionType:
            captured_type = None

            def mock_set_baggage(key, value, context=None):
                nonlocal captured_type
                if key == ATTR_EXTENSION_TYPE:
                    captured_type = value
                return context or MagicMock()

            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.baggage"
            ) as mock_baggage:
                with patch("sap_cloud_sdk.core.telemetry.extensions.get_current"):
                    with patch("sap_cloud_sdk.core.telemetry.extensions.attach"):
                        with patch("sap_cloud_sdk.core.telemetry.extensions.detach"):
                            mock_baggage.set_baggage = mock_set_baggage

                            with extension_context("cap", "ext_name", extension_type):
                                pass

            assert captured_type == extension_type.value

    def test_extension_context_with_various_extension_names(self):
        """Test extension_context with various extension name formats."""
        test_names = [
            "ServiceNow Extension",
            "Jira Integration",
            "Custom HR Tool",
            "simple-name",
        ]

        for ext_name in test_names:
            captured_name = None

            def mock_set_baggage(key, value, context=None):
                nonlocal captured_name
                if key == ATTR_EXTENSION_NAME:
                    captured_name = value
                return context or MagicMock()

            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.baggage"
            ) as mock_baggage:
                with patch("sap_cloud_sdk.core.telemetry.extensions.get_current"):
                    with patch("sap_cloud_sdk.core.telemetry.extensions.attach"):
                        with patch("sap_cloud_sdk.core.telemetry.extensions.detach"):
                            mock_baggage.set_baggage = mock_set_baggage

                            with extension_context("cap", ext_name, ExtensionType.TOOL):
                                pass

            assert captured_name == ext_name

    def test_extension_context_with_various_capability_ids(self):
        """Test extension_context with various capability IDs."""
        test_capability_ids = [
            "default",
            "hr-management",
            "custom.capability.v2",
        ]

        for capability_id in test_capability_ids:
            captured_cap = None

            def mock_set_baggage(key, value, context=None):
                nonlocal captured_cap
                if key == ATTR_CAPABILITY_ID:
                    captured_cap = value
                return context or MagicMock()

            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.baggage"
            ) as mock_baggage:
                with patch("sap_cloud_sdk.core.telemetry.extensions.get_current"):
                    with patch("sap_cloud_sdk.core.telemetry.extensions.attach"):
                        with patch("sap_cloud_sdk.core.telemetry.extensions.detach"):
                            mock_baggage.set_baggage = mock_set_baggage

                            with extension_context(
                                capability_id, "ext_name", ExtensionType.TOOL
                            ):
                                pass

            assert captured_cap == capability_id

    def test_extension_context_nested(self):
        """Test nested extension_context calls."""
        attach_calls = []
        detach_calls = []

        def mock_attach(ctx):
            token = f"token_{len(attach_calls)}"
            attach_calls.append(token)
            return token

        def mock_detach(token):
            detach_calls.append(token)

        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.get_current"
            ) as mock_get_current:
                with patch(
                    "sap_cloud_sdk.core.telemetry.extensions.attach",
                    side_effect=mock_attach,
                ):
                    with patch(
                        "sap_cloud_sdk.core.telemetry.extensions.detach",
                        side_effect=mock_detach,
                    ):
                        mock_ctx = MagicMock()
                        mock_get_current.return_value = mock_ctx
                        mock_baggage.set_baggage.return_value = mock_ctx

                        with extension_context(
                            "outer_cap",
                            "outer_ext",
                            ExtensionType.INSTRUCTION,
                        ):
                            with extension_context(
                                "inner_cap", "inner_ext", ExtensionType.TOOL
                            ):
                                pass

        assert len(attach_calls) == 2
        assert len(detach_calls) == 2
        # Detach should be in reverse order (LIFO)
        assert detach_calls == ["token_1", "token_0"]


class TestGetExtensionContext:
    """Test suite for get_extension_context function."""

    def test_returns_none_when_not_in_context(self):
        """Test returns None when not in extension context."""
        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            mock_baggage.get_baggage.return_value = None
            result = get_extension_context()
            assert result is None

    def test_returns_none_when_is_extension_not_true(self):
        """Test returns None when isExtension is not 'true'."""
        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            mock_baggage.get_baggage.return_value = "false"
            result = get_extension_context()
            assert result is None

    def test_returns_dict_when_in_context(self):
        """Test returns dict with all extension metadata."""

        def mock_get_baggage(key):
            values = {
                ATTR_IS_EXTENSION: "true",
                ATTR_EXTENSION_TYPE: "tool",
                ATTR_CAPABILITY_ID: "default",
                ATTR_EXTENSION_ID: "uuid-123",
                ATTR_EXTENSION_NAME: "ServiceNow Extension",
                ATTR_EXTENSION_VERSION: "3",
                ATTR_EXTENSION_ITEM_NAME: "create_ticket",
                ATTR_EXTENSION_URL: "https://ext.example.com",
                ATTR_SOLUTION_ID: "sol-789",
            }
            return values.get(key)

        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            mock_baggage.get_baggage = mock_get_baggage
            result = get_extension_context()

            assert result is not None
            assert result["is_extension"] is True
            assert result["extension_type"] == "tool"
            assert result["capability_id"] == "default"
            assert result["extension_id"] == "uuid-123"
            assert result["extension_name"] == "ServiceNow Extension"
            assert result["extension_version"] == "3"
            assert result["item_name"] == "create_ticket"
            assert result["extension_url"] == "https://ext.example.com"
            assert result["solution_id"] == "sol-789"

    def test_with_different_extension_types(self):
        """Test get_extension_context with different extension types."""
        for extension_type in ExtensionType:

            def mock_get_baggage(key, et_val=extension_type.value):
                values = {
                    ATTR_IS_EXTENSION: "true",
                    ATTR_EXTENSION_TYPE: et_val,
                    ATTR_CAPABILITY_ID: "cap",
                    ATTR_EXTENSION_ID: "uuid",
                    ATTR_EXTENSION_NAME: "ext_name",
                    ATTR_EXTENSION_VERSION: "1",
                    ATTR_EXTENSION_ITEM_NAME: "item",
                }
                return values.get(key)

            with patch(
                "sap_cloud_sdk.core.telemetry.extensions.baggage"
            ) as mock_baggage:
                mock_baggage.get_baggage = mock_get_baggage
                result = get_extension_context()
                assert result is not None
                assert result["extension_type"] == extension_type.value

    def test_with_none_extension_name(self):
        """Test get_extension_context when extension_name is None."""

        def mock_get_baggage(key):
            values = {
                ATTR_IS_EXTENSION: "true",
                ATTR_EXTENSION_TYPE: "tool",
                ATTR_CAPABILITY_ID: "default",
                ATTR_EXTENSION_ID: "uuid",
                ATTR_EXTENSION_NAME: None,
                ATTR_EXTENSION_VERSION: "",
                ATTR_EXTENSION_ITEM_NAME: "",
            }
            return values.get(key)

        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            mock_baggage.get_baggage = mock_get_baggage
            result = get_extension_context()

            assert result is not None
            assert result["is_extension"] is True
            assert result["extension_name"] is None
            assert result["extension_type"] == "tool"

    def test_with_none_extension_type(self):
        """Test get_extension_context when extension_type is None."""

        def mock_get_baggage(key):
            values = {
                ATTR_IS_EXTENSION: "true",
                ATTR_EXTENSION_TYPE: None,
                ATTR_CAPABILITY_ID: "default",
                ATTR_EXTENSION_ID: "uuid",
                ATTR_EXTENSION_NAME: "ext_name",
                ATTR_EXTENSION_VERSION: "1",
                ATTR_EXTENSION_ITEM_NAME: "item",
            }
            return values.get(key)

        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            mock_baggage.get_baggage = mock_get_baggage
            result = get_extension_context()

            assert result is not None
            assert result["is_extension"] is True
            assert result["extension_type"] is None
            assert result["extension_name"] == "ext_name"

    def test_with_none_capability_id(self):
        """Test get_extension_context when capability_id is None."""

        def mock_get_baggage(key):
            values = {
                ATTR_IS_EXTENSION: "true",
                ATTR_EXTENSION_TYPE: "tool",
                ATTR_CAPABILITY_ID: None,
                ATTR_EXTENSION_ID: "uuid",
                ATTR_EXTENSION_NAME: "ext_name",
                ATTR_EXTENSION_VERSION: "1",
                ATTR_EXTENSION_ITEM_NAME: "item",
            }
            return values.get(key)

        with patch("sap_cloud_sdk.core.telemetry.extensions.baggage") as mock_baggage:
            mock_baggage.get_baggage = mock_get_baggage
            result = get_extension_context()

            assert result is not None
            assert result["is_extension"] is True
            assert result["capability_id"] is None


class TestExtensionContextIntegration:
    """Integration tests using real OTel baggage (no mocks)."""

    def test_extension_context_and_get_work_together(self):
        """Test that extension_context sets values get_extension_context reads."""
        result_before = get_extension_context()
        assert result_before is None

        with extension_context(
            "default",
            "ServiceNow Extension",
            ExtensionType.TOOL,
            extension_id="uuid-sn",
            extension_version="2",
            item_name="create_ticket",
            extension_url="https://ext.example.com",
            solution_id="sol-789",
        ):
            result_during = get_extension_context()
            assert result_during is not None
            assert result_during["is_extension"] is True
            assert result_during["capability_id"] == "default"
            assert result_during["extension_name"] == "ServiceNow Extension"
            assert result_during["extension_type"] == "tool"
            assert result_during["extension_id"] == "uuid-sn"
            assert result_during["extension_version"] == "2"
            assert result_during["item_name"] == "create_ticket"
            assert result_during["extension_url"] == "https://ext.example.com"
            assert result_during["solution_id"] == "sol-789"

        result_after = get_extension_context()
        assert result_after is None

    def test_nested_extension_contexts(self):
        """Test nested extension contexts with real OTel baggage."""
        with extension_context(
            "outer_cap",
            "outer_ext",
            ExtensionType.INSTRUCTION,
            extension_id="uuid-outer",
            extension_version="1",
            item_name="outer_item",
        ):
            outer = get_extension_context()
            assert outer is not None
            assert outer["capability_id"] == "outer_cap"
            assert outer["extension_name"] == "outer_ext"
            assert outer["extension_type"] == "instruction"
            assert outer["extension_id"] == "uuid-outer"
            assert outer["extension_version"] == "1"
            assert outer["item_name"] == "outer_item"

            with extension_context(
                "inner_cap",
                "inner_ext",
                ExtensionType.TOOL,
                extension_id="uuid-inner",
                extension_version="5",
                item_name="inner_tool",
            ):
                inner = get_extension_context()
                assert inner is not None
                assert inner["capability_id"] == "inner_cap"
                assert inner["extension_name"] == "inner_ext"
                assert inner["extension_type"] == "tool"
                assert inner["extension_id"] == "uuid-inner"
                assert inner["extension_version"] == "5"
                assert inner["item_name"] == "inner_tool"

            after_inner = get_extension_context()
            assert after_inner is not None
            assert after_inner["capability_id"] == "outer_cap"
            assert after_inner["extension_name"] == "outer_ext"
            assert after_inner["extension_type"] == "instruction"

        final = get_extension_context()
        assert final is None

    def test_extension_context_defaults_integration(self):
        """Test extension_context with only required params using real OTel."""
        with extension_context("default", "my-ext", ExtensionType.HOOK):
            result = get_extension_context()
            assert result is not None
            assert result["is_extension"] is True
            assert result["extension_type"] == "hook"
            assert result["capability_id"] == "default"
            assert result["extension_name"] == "my-ext"
            assert result["extension_id"] == ""
            assert result["extension_version"] == ""
            assert result["item_name"] == ""
            assert result["extension_url"] == ""
            assert result["solution_id"] == ""


# ---------------------------------------------------------------------------
# resolve_source_info
# ---------------------------------------------------------------------------


class TestResolveSourceInfo:
    """Tests for resolve_source_info."""

    def test_none_mapping_returns_fallback(self):
        name, ext_id, ver, url, sid = resolve_source_info("key", None, "fallback")
        assert name == "fallback"
        assert ext_id == ""
        assert ver == ""
        assert url == ""
        assert sid == ""

    def test_missing_key_returns_fallback(self):
        name, ext_id, ver, url, sid = resolve_source_info(
            "missing", {"other": {}}, "fb"
        )
        assert name == "fb"

    def test_empty_fallback_returns_unknown(self):
        name, _, _, _, _ = resolve_source_info("missing", None, "")
        assert name == "unknown"

    def test_dataclass_source_info(self):
        @dataclass
        class FakeSourceInfo:
            extension_name: str
            extension_id: str
            extension_version: str

        info = FakeSourceInfo("My Ext", "uuid-1", "3")
        name, ext_id, ver, url, sid = resolve_source_info("k", {"k": info}, "fb")
        assert name == "My Ext"
        assert ext_id == "uuid-1"
        assert ver == "3"
        assert url == ""
        assert sid == ""

    def test_dataclass_empty_name_uses_fallback(self):
        @dataclass
        class FakeSourceInfo:
            extension_name: str
            extension_id: str
            extension_version: str

        info = FakeSourceInfo("", "uuid-1", "3")
        name, _, _, _, _ = resolve_source_info("k", {"k": info}, "fb")
        assert name == "fb"

    def test_dict_source_info(self):
        info = {
            "extensionName": "Dict Ext",
            "extensionId": "uuid-2",
            "extensionVersion": "5",
        }
        name, ext_id, ver, url, sid = resolve_source_info("k", {"k": info}, "fb")
        assert name == "Dict Ext"
        assert ext_id == "uuid-2"
        assert ver == "5"
        assert url == ""
        assert sid == ""

    def test_dict_empty_name_uses_fallback(self):
        info = {"extensionName": "", "extensionId": "x", "extensionVersion": "1"}
        name, _, _, _, _ = resolve_source_info("k", {"k": info}, "fb")
        assert name == "fb"

    def test_unknown_type_returns_fallback(self):
        name, ext_id, ver, url, sid = resolve_source_info("k", {"k": 42}, "fb")
        assert name == "fb"
        assert ext_id == ""
        assert ver == ""
        assert url == ""
        assert sid == ""

    def test_dataclass_none_version(self):
        @dataclass
        class FakeSourceInfo:
            extension_name: str
            extension_id: str
            extension_version: str | None

        info = FakeSourceInfo("Ext", "id", None)
        _, _, ver, _, _ = resolve_source_info("k", {"k": info}, "fb")
        assert ver == ""

    def test_dataclass_with_url_and_solution_id(self):
        @dataclass
        class FakeSourceInfo:
            extension_name: str
            extension_id: str
            extension_version: str
            extension_url: str
            solution_id: str

        info = FakeSourceInfo("Ext", "id", "1", "https://url", "sol-123")
        _, _, _, url, sid = resolve_source_info("k", {"k": info}, "fb")
        assert url == "https://url"
        assert sid == "sol-123"

    def test_dict_with_url_and_solution_id(self):
        info = {
            "extensionName": "Ext",
            "extensionId": "id",
            "extensionVersion": "1",
            "extensionUrl": "https://url",
            "solutionId": "sol-456",
        }
        _, _, _, url, sid = resolve_source_info("k", {"k": info}, "fb")
        assert url == "https://url"
        assert sid == "sol-456"


# ---------------------------------------------------------------------------
# build_extension_span_attributes
# ---------------------------------------------------------------------------


class TestBuildExtensionSpanAttributes:
    """Tests for build_extension_span_attributes."""

    def test_returns_all_seven_keys(self):
        attrs = build_extension_span_attributes(
            "Ext", "id-1", "2", ExtensionType.TOOL, "default", "my_tool"
        )
        assert attrs[ATTR_IS_EXTENSION] is True
        assert attrs[ATTR_EXTENSION_TYPE] == "tool"
        assert attrs[ATTR_CAPABILITY_ID] == "default"
        assert attrs[ATTR_EXTENSION_ID] == "id-1"
        assert attrs[ATTR_EXTENSION_NAME] == "Ext"
        assert attrs[ATTR_EXTENSION_VERSION] == "2"
        assert attrs[ATTR_EXTENSION_ITEM_NAME] == "my_tool"

    def test_hook_type(self):
        attrs = build_extension_span_attributes(
            "Ext", "", "", ExtensionType.HOOK, "cap", "hook_name"
        )
        assert attrs[ATTR_EXTENSION_TYPE] == "hook"

    def test_includes_solution_id_when_provided(self):
        attrs = build_extension_span_attributes(
            "Ext",
            "id",
            "1",
            ExtensionType.TOOL,
            "default",
            "tool",
            extension_url="https://url",
            solution_id="sol-123",
        )
        assert attrs["sap.extension.solution_id"] == "sol-123"
        assert attrs["sap.extension.extensionUrl"] == "https://url"

    def test_omits_solution_id_when_empty(self):
        attrs = build_extension_span_attributes(
            "Ext",
            "id",
            "1",
            ExtensionType.TOOL,
            "default",
            "tool",
        )
        assert "sap.extension.solution_id" not in attrs
        assert "sap.extension.extensionUrl" not in attrs


# ---------------------------------------------------------------------------
# Tool call metrics
# ---------------------------------------------------------------------------


class TestToolCallMetrics:
    """Tests for tool call duration tracking."""

    def test_no_reset_returns_zero(self):
        # Use a fresh context by not calling reset
        count, duration = get_tool_call_metrics()
        # May or may not be zero depending on prior test state, but shouldn't crash
        assert isinstance(count, int)
        assert isinstance(duration, (int, float))

    def test_reset_and_record(self):
        reset_tool_call_metrics()
        record_tool_call_duration(0.1)
        record_tool_call_duration(0.2)
        count, total_ms = get_tool_call_metrics()
        assert count == 2
        assert abs(total_ms - 300.0) < 1.0

    def test_record_noop_without_reset(self):
        """record_tool_call_duration silently no-ops if never reset."""
        from sap_cloud_sdk.core.telemetry.extensions import _tool_call_durations

        # Remove the ContextVar value to simulate never-reset state
        tok = _tool_call_durations.set([])
        _tool_call_durations.reset(tok)
        # Should not raise
        record_tool_call_duration(1.0)


# ---------------------------------------------------------------------------
# Hook call metrics
# ---------------------------------------------------------------------------


class TestHookCallMetrics:
    """Tests for hook call duration tracking."""

    def test_reset_and_record(self):
        reset_hook_call_metrics()
        record_hook_call_duration(0.05)
        count, total_ms = get_hook_call_metrics()
        assert count == 1
        assert abs(total_ms - 50.0) < 1.0

    def test_record_noop_without_reset(self):
        from sap_cloud_sdk.core.telemetry.extensions import _hook_call_durations

        tok = _hook_call_durations.set([])
        _hook_call_durations.reset(tok)
        record_hook_call_duration(1.0)

    def test_independent_from_tool_metrics(self):
        """Hook and tool accumulators do not interfere with each other."""
        reset_tool_call_metrics()
        reset_hook_call_metrics()
        record_tool_call_duration(0.1)
        record_tool_call_duration(0.2)
        record_hook_call_duration(0.05)

        tool_count, tool_ms = get_tool_call_metrics()
        hook_count, hook_ms = get_hook_call_metrics()

        assert tool_count == 2
        assert hook_count == 1
        assert abs(tool_ms - 300.0) < 1.0
        assert abs(hook_ms - 50.0) < 1.0


# ---------------------------------------------------------------------------
# call_extension_tool
# ---------------------------------------------------------------------------


class TestCallExtensionTool:
    """Tests for call_extension_tool."""

    def test_calls_mcp_client(self):
        async def _run():
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = "result-123"

            reset_tool_call_metrics()
            result = await call_extension_tool(
                mcp_client=mock_client,
                tool_name="create_ticket",
                args={"title": "Bug"},
                extension_name="ServiceNow",
            )
            assert result == "result-123"
            mock_client.call_tool.assert_awaited_once_with(
                "create_ticket", {"title": "Bug"}
            )
            count, _ = get_tool_call_metrics()
            assert count == 1

        asyncio.run(_run())

    def test_uses_source_mapping(self):
        async def _run():
            @dataclass
            class FakeSourceInfo:
                extension_name: str
                extension_id: str
                extension_version: str

            mapping = {"prefix_tool1": FakeSourceInfo("Mapped Ext", "uuid-m", "7")}
            mock_client = AsyncMock()
            mock_client.call_tool.return_value = "ok"

            reset_tool_call_metrics()
            result = await call_extension_tool(
                mcp_client=mock_client,
                tool_name="tool1",
                args={},
                extension_name="Fallback",
                source_mapping=mapping,
                tool_prefix="prefix_",
            )
            assert result == "ok"

        asyncio.run(_run())

    def test_records_duration_on_error(self):
        async def _run():
            mock_client = AsyncMock()
            mock_client.call_tool.side_effect = RuntimeError("fail")

            reset_tool_call_metrics()
            with pytest.raises(RuntimeError, match="fail"):
                await call_extension_tool(
                    mcp_client=mock_client,
                    tool_name="t",
                    args={},
                    extension_name="E",
                )
            count, _ = get_tool_call_metrics()
            assert count == 1  # Duration still recorded

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# call_extension_hook
# ---------------------------------------------------------------------------


class TestCallExtensionHook:
    """Tests for call_extension_hook."""

    def test_calls_extensibility_client(self):
        async def _run():
            mock_client = AsyncMock()
            mock_client.call_hook.return_value = {"status": "ok"}
            mock_hook = MagicMock()
            mock_hook.name = "pre_process"

            reset_hook_call_metrics()
            result = await call_extension_hook(
                extensibility_client=mock_client,
                hook=mock_hook,
                payload={"data": 1},
                extension_name="My Ext",
            )
            assert result == {"status": "ok"}
            mock_client.call_hook.assert_awaited_once_with(mock_hook, {"data": 1})
            count, _ = get_hook_call_metrics()
            assert count == 1

        asyncio.run(_run())

    def test_hook_without_name_uses_hook_id(self):
        async def _run():
            mock_client = AsyncMock()
            mock_client.call_hook.return_value = None
            mock_hook = object()  # No .name attribute

            reset_hook_call_metrics()
            await call_extension_hook(
                extensibility_client=mock_client,
                hook=mock_hook,
                payload={},
                extension_name="Ext",
                hook_id="ord:hook:1",
            )
            count, _ = get_hook_call_metrics()
            assert count == 1

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# emit_extensions_summary_span
# ---------------------------------------------------------------------------


class TestEmitExtensionsSummarySpan:
    """Tests for emit_extensions_summary_span."""

    def test_creates_span_with_attributes(self):
        with patch("sap_cloud_sdk.core.telemetry.extensions._tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_span.return_value = mock_span

            emit_extensions_summary_span(
                tool_call_count=3,
                hook_call_count=2,
                has_instruction=True,
                total_duration_ms=1500.0,
            )

            mock_tracer.start_span.assert_called_once()
            call_args = mock_tracer.start_span.call_args
            assert call_args[0][0] == "agent_extensions_summary"
            attrs = call_args[1]["attributes"]
            assert attrs[ATTR_SUMMARY_TOTAL_OPERATION_COUNT] == 6  # 3+2+1
            assert attrs[ATTR_SUMMARY_TOTAL_DURATION_MS] == 1500.0
            assert attrs[ATTR_SUMMARY_TOOL_CALL_COUNT] == 3
            assert attrs[ATTR_SUMMARY_HOOK_CALL_COUNT] == 2
            assert attrs[ATTR_SUMMARY_HAS_INSTRUCTION] is True
            mock_span.end.assert_called_once()

    def test_no_instruction_count(self):
        with patch("sap_cloud_sdk.core.telemetry.extensions._tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_span.return_value = mock_span

            emit_extensions_summary_span(
                tool_call_count=1,
                hook_call_count=0,
                has_instruction=False,
                total_duration_ms=100.0,
            )

            attrs = mock_tracer.start_span.call_args[1]["attributes"]
            assert attrs[ATTR_SUMMARY_TOTAL_OPERATION_COUNT] == 1  # no +1


# ---------------------------------------------------------------------------
# ExtensionContextLogFilter
# ---------------------------------------------------------------------------


class TestExtensionContextLogFilter:
    """Tests for ExtensionContextLogFilter."""

    def test_adds_attributes_in_extension_context(self):
        filt = ExtensionContextLogFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)

        with extension_context(
            "cap",
            "ext",
            ExtensionType.TOOL,
            extension_id="id1",
            extension_version="2",
            item_name="tool1",
            extension_url="https://ext.example.com",
            solution_id="sol-42",
        ):
            result = filt.filter(record)

        assert result is True
        assert getattr(record, "ext_is_extension") == "true"
        assert getattr(record, "ext_extension_type") == "tool"
        assert getattr(record, "ext_capability_id") == "cap"
        assert getattr(record, "ext_extension_name") == "ext"
        assert getattr(record, "ext_extension_id") == "id1"
        assert getattr(record, "ext_extension_version") == "2"
        assert getattr(record, "ext_item_name") == "tool1"
        assert getattr(record, "ext_extension_url") == "https://ext.example.com"
        assert getattr(record, "ext_solution_id") == "sol-42"

    def test_no_attributes_outside_context(self):
        filt = ExtensionContextLogFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        result = filt.filter(record)
        assert result is True
        assert not hasattr(record, "ext_is_extension")

    def test_always_returns_true(self):
        """Filter never suppresses log records, even outside extension context."""
        filt = ExtensionContextLogFilter()
        for level in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR):
            record = logging.LogRecord("t", level, "", 0, "m", (), None)
            assert filt.filter(record) is True

    def test_empty_values_set_as_empty_string(self):
        """When baggage values are empty, attributes are set to empty string."""
        filt = ExtensionContextLogFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)

        with extension_context(
            "cap",
            "ext",
            ExtensionType.TOOL,
            extension_id="",
            extension_version="",
            item_name="",
        ):
            filt.filter(record)

        assert getattr(record, "ext_extension_id") == ""
        assert getattr(record, "ext_extension_version") == ""
        assert getattr(record, "ext_item_name") == ""
        assert getattr(record, "ext_extension_url") == ""
        assert getattr(record, "ext_solution_id") == ""
