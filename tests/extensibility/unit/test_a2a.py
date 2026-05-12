"""Tests for A2A card serialization helpers."""

import logging


from a2a.types import AgentExtension

from sap_cloud_sdk.extensibility._a2a import (
    EXTENSION_CAPABILITY_SCHEMA_VERSION,
    _to_camel_case,
    _tools_to_dict,
    _supported_hooks_to_dict,
    _validate_extension_capabilities,
    build_extension_capabilities,
)
from sap_cloud_sdk.extensibility._models import (
    ExtensionCapability,
    HookCapability,
    ToolAdditions,
    Tools,
    HookType,
)


class TestExtensionCapabilitySchemaVersion:
    """Tests for the EXTENSION_CAPABILITY_SCHEMA_VERSION constant."""

    def test_schema_version_is_integer(self):
        assert isinstance(EXTENSION_CAPABILITY_SCHEMA_VERSION, int)

    def test_schema_version_value(self):
        assert EXTENSION_CAPABILITY_SCHEMA_VERSION == 1

    def test_schema_version_exported_from_package(self):
        from sap_cloud_sdk.extensibility import (
            EXTENSION_CAPABILITY_SCHEMA_VERSION as exported,
        )

        assert exported == 1


class TestToCamelCase:
    """Tests for the _to_camel_case helper."""

    def test_single_word(self):
        assert _to_camel_case("enabled") == "enabled"

    def test_two_words(self):
        assert _to_camel_case("display_name") == "displayName"

    def test_three_words(self):
        assert _to_camel_case("my_long_name") == "myLongName"

    def test_already_camel(self):
        # Single word — no underscores — passes through unchanged.
        assert _to_camel_case("displayName") == "displayName"


class TestToolsToDict:
    """Tests for the _tools_to_dict helper."""

    def test_default_tools(self):
        tools = Tools()
        result = _tools_to_dict(tools)
        assert result == {"additions": {"enabled": True}}

    def test_custom_tools(self):
        tools = Tools(additions=ToolAdditions(enabled=False))
        result = _tools_to_dict(tools)
        assert result == {"additions": {"enabled": False}}


class TestValidateExtensionCapabilities:
    """Tests for _validate_extension_capabilities()."""

    def test_empty_list_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            _validate_extension_capabilities([])

        assert "empty list" in caplog.text

    def test_single_valid_capability_no_warnings(self, caplog):
        caps = [
            ExtensionCapability(
                display_name="Test",
                description="A test capability.",
            )
        ]
        with caplog.at_level(logging.WARNING):
            _validate_extension_capabilities(caps)

        assert caplog.text == ""

    def test_duplicate_ids_logs_warning(self, caplog):
        caps = [
            ExtensionCapability(
                display_name="First",
                description="First capability.",
                id="same-id",
            ),
            ExtensionCapability(
                display_name="Second",
                description="Second capability.",
                id="same-id",
            ),
        ]
        with caplog.at_level(logging.WARNING):
            _validate_extension_capabilities(caps)

        assert "Duplicate" in caplog.text
        assert "same-id" in caplog.text
        assert "0" in caplog.text  # first index
        assert "1" in caplog.text  # second index

    def test_empty_id_logs_warning(self, caplog):
        caps = [
            ExtensionCapability(
                display_name="Bad",
                description="Has empty ID.",
                id="",
            ),
        ]
        with caplog.at_level(logging.WARNING):
            _validate_extension_capabilities(caps)

        assert "empty" in caplog.text.lower()

    def test_whitespace_only_id_logs_warning(self, caplog):
        caps = [
            ExtensionCapability(
                display_name="Bad",
                description="Has whitespace-only ID.",
                id="   ",
            ),
        ]
        with caplog.at_level(logging.WARNING):
            _validate_extension_capabilities(caps)

        assert "whitespace" in caplog.text.lower()

    def test_multiple_duplicates_each_logged(self, caplog):
        caps = [
            ExtensionCapability(display_name="A", description="A.", id="dup"),
            ExtensionCapability(display_name="B", description="B.", id="dup"),
            ExtensionCapability(display_name="C", description="C.", id="dup"),
        ]
        with caplog.at_level(logging.WARNING):
            _validate_extension_capabilities(caps)

        # Should warn about index 1 and index 2 being duplicates of index 0
        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert len(warning_messages) == 2


class TestBuildExtensionCapabilities:
    """Tests for build_extension_capabilities()."""

    def test_single_default_capability(self):
        caps = [
            ExtensionCapability(
                display_name="Default",
                description="Extension capability to further enhance agent.",
            )
        ]

        result = build_extension_capabilities(caps)

        assert len(result) == 1
        ext = result[0]
        assert isinstance(ext, AgentExtension)
        assert ext.uri == "urn:sap:extension-capability:v1:default"
        assert ext.description == "Extension capability to further enhance agent."
        assert ext.required is False
        assert ext.params == {
            "capabilityId": "default",
            "displayName": "Default",
            "instructionSupported": True,
            "tools": {
                "additions": {
                    "enabled": True,
                },
            },
            "supportedHooks": [],
        }

    def test_uri_generation_with_custom_id(self):
        caps = [
            ExtensionCapability(
                display_name="Doc Processing",
                description="Document processing pipeline.",
                id="doc-processing",
            )
        ]

        result = build_extension_capabilities(caps)

        assert result[0].uri == ("urn:sap:extension-capability:v1:doc-processing")

    def test_uri_includes_schema_version(self):
        """URI embeds the current schema version."""
        caps = [
            ExtensionCapability(
                display_name="Test",
                description="Test.",
            )
        ]

        result = build_extension_capabilities(caps)

        expected_version = f"v{EXTENSION_CAPABILITY_SCHEMA_VERSION}"
        assert expected_version in result[0].uri

    def test_params_camel_case_conversion(self):
        """Verify that params keys use camelCase."""
        caps = [
            ExtensionCapability(
                display_name="My Cap",
                description="A capability.",
                instruction_supported=False,
                tools=Tools(additions=ToolAdditions(enabled=False)),
                supported_hooks=[
                    HookCapability(
                        id="pre_test_hook",
                        type=HookType.BEFORE,
                        display_name="Test Pre Hook",
                        description="Test description",
                    ),
                    HookCapability(
                        id="post_test_hook",
                        type=HookType.AFTER,
                        display_name="Test Post Hook",
                        description="Test description",
                    ),
                ],
            )
        ]

        result = build_extension_capabilities(caps)
        params = result[0].params
        assert params is not None

        # camelCase keys
        assert "capabilityId" in params
        assert "displayName" in params
        assert "instructionSupported" in params
        assert "tools" in params
        assert "supportedHooks" in params

        # No snake_case keys
        assert "capability_id" not in params
        assert "display_name" not in params
        assert "instruction_supported" not in params
        assert "supported_hooks" not in params

        # Values
        assert params["capabilityId"] == "default"
        assert params["displayName"] == "My Cap"
        assert params["instructionSupported"] is False
        assert params["tools"]["additions"]["enabled"] is False
        assert params["supportedHooks"][0]["id"] == "pre_test_hook"
        assert params["supportedHooks"][0]["type"] == "BEFORE"
        assert params["supportedHooks"][1]["id"] == "post_test_hook"
        assert params["supportedHooks"][1]["type"] == "AFTER"

    def test_tool_additions_nested_under_additions_key(self):
        """Verify tools dict has 'additions' wrapper matching the design spec."""
        caps = [
            ExtensionCapability(
                display_name="Test",
                description="Test.",
                tools=Tools(additions=ToolAdditions(enabled=True)),
            )
        ]

        result = build_extension_capabilities(caps)
        assert result[0].params is not None

        tools = result[0].params["tools"]
        assert "additions" in tools
        assert tools["additions"] == {"enabled": True}

    def test_multiple_capabilities(self):
        caps = [
            ExtensionCapability(
                display_name="Onboarding",
                description="Onboarding workflow extensions.",
                id="onboarding",
            ),
            ExtensionCapability(
                display_name="Doc Processing",
                description="Document processing pipeline.",
                id="doc-processing",
                instruction_supported=False,
                tools=Tools(additions=ToolAdditions(enabled=True)),
            ),
            ExtensionCapability(
                display_name="Invoice Processing",
                description="Invoice processing pipeline.",
                id="invoice-processing",
                instruction_supported=False,
                tools=Tools(additions=ToolAdditions(enabled=False)),
                supported_hooks=[
                    HookCapability(
                        id="before_invoice_hook",
                        type=HookType.BEFORE,
                        display_name="Before Invoice Hook",
                        description="Hook executed before invoice processing.",
                    )
                ],
            ),
        ]

        result = build_extension_capabilities(caps)

        assert len(result) == 3

        assert result[0].uri == ("urn:sap:extension-capability:v1:onboarding")
        assert result[0].params is not None
        assert result[0].params["capabilityId"] == "onboarding"
        assert result[0].params["displayName"] == "Onboarding"

        assert result[1].uri == ("urn:sap:extension-capability:v1:doc-processing")
        assert result[1].params is not None
        assert result[1].params["capabilityId"] == "doc-processing"
        assert result[1].params["instructionSupported"] is False
        assert result[1].params["tools"]["additions"]["enabled"] is True

        assert result[2].uri == ("urn:sap:extension-capability:v1:invoice-processing")
        assert result[2].params is not None
        assert result[2].params["capabilityId"] == "invoice-processing"
        assert result[2].params["supportedHooks"][0]["id"] == "before_invoice_hook"
        assert result[2].params["supportedHooks"][0]["type"] == "BEFORE"

    def test_empty_list_returns_empty(self):
        result = build_extension_capabilities([])
        assert result == []

    def test_required_always_false(self):
        caps = [
            ExtensionCapability(
                display_name="Test",
                description="Test.",
            )
        ]

        result = build_extension_capabilities(caps)

        assert result[0].required is False

    def test_description_passed_through(self):
        desc = "This is a detailed description of the extension capability."
        caps = [
            ExtensionCapability(
                display_name="Test",
                description=desc,
            )
        ]

        result = build_extension_capabilities(caps)

        assert result[0].description == desc

    def test_validation_runs_before_conversion(self, caplog):
        """Validation warnings are logged but conversion still proceeds."""
        caps = [
            ExtensionCapability(
                display_name="Dup1",
                description="First.",
                id="dup",
            ),
            ExtensionCapability(
                display_name="Dup2",
                description="Second.",
                id="dup",
            ),
        ]

        with caplog.at_level(logging.WARNING):
            result = build_extension_capabilities(caps)

        # Warning logged
        assert "Duplicate" in caplog.text
        # But both are still converted
        assert len(result) == 2

    def test_return_type_is_list_of_agent_extension(self):
        caps = [
            ExtensionCapability(
                display_name="Test",
                description="Test.",
            )
        ]

        result = build_extension_capabilities(caps)

        assert isinstance(result, list)
        assert all(isinstance(ext, AgentExtension) for ext in result)

    def test_instruction_supported_true(self):
        caps = [
            ExtensionCapability(
                display_name="Test",
                description="Test.",
                instruction_supported=True,
            )
        ]

        result = build_extension_capabilities(caps)
        assert result[0].params is not None

        assert result[0].params["instructionSupported"] is True

    def test_instruction_supported_false(self):
        caps = [
            ExtensionCapability(
                display_name="Test",
                description="Test.",
                instruction_supported=False,
            )
        ]

        result = build_extension_capabilities(caps)
        assert result[0].params is not None

        assert result[0].params["instructionSupported"] is False

    def test_matches_design_spec_example(self):
        """Verify output matches the exact example from the design spec."""
        caps = [
            ExtensionCapability(
                id="default",
                display_name="Default",
                description="Extension capability to further enhance agent. ...",
                instruction_supported=True,
                tools=Tools(additions=ToolAdditions(enabled=True)),
                supported_hooks=[
                    HookCapability(
                        id="pre_test_hook",
                        type=HookType.BEFORE,
                        display_name="Test Pre Hook",
                        description="Test description",
                    )
                ],
            )
        ]

        result = build_extension_capabilities(caps)

        ext = result[0]
        assert ext.uri == "urn:sap:extension-capability:v1:default"
        assert ext.description == "Extension capability to further enhance agent. ..."
        assert ext.required is False
        assert ext.params == {
            "capabilityId": "default",
            "instructionSupported": True,
            "displayName": "Default",
            "tools": {
                "additions": {
                    "enabled": True,
                },
            },
            "supportedHooks": [
                {
                    "id": "pre_test_hook",
                    "type": "BEFORE",
                    "displayName": "Test Pre Hook",
                    "description": "Test description",
                }
            ],
        }


class TestSupportedHooksToDict:
    """Tests for the _supported_hooks_to_dict helper."""

    def test_empty_list(self):
        result = _supported_hooks_to_dict([])
        assert result == []

    def test_single_hook(self):
        hooks = [
            HookCapability(
                id="before_tool_execution",
                type=HookType.BEFORE,
                display_name="Before Tool Execution",
                description="Hook that runs before tool execution",
            )
        ]
        result = _supported_hooks_to_dict(hooks)
        assert result == [
            {
                "id": "before_tool_execution",
                "type": "BEFORE",
                "displayName": "Before Tool Execution",
                "description": "Hook that runs before tool execution",
            }
        ]

    def test_multiple_hooks(self):
        hooks = [
            HookCapability(
                id="before_hook",
                type=HookType.BEFORE,
                display_name="Before Hook",
                description="Before hook description",
            ),
            HookCapability(
                id="after_hook",
                type=HookType.AFTER,
                display_name="After Hook",
                description="After hook description",
            ),
        ]
        result = _supported_hooks_to_dict(hooks)
        assert len(result) == 2
        assert result[0]["id"] == "before_hook"
        assert result[0]["type"] == "BEFORE"
        assert result[0]["displayName"] == "Before Hook"
        assert result[1]["id"] == "after_hook"
        assert result[1]["type"] == "AFTER"
        assert result[1]["displayName"] == "After Hook"

    def test_camel_case_conversion(self):
        """Verify that hook fields are converted to camelCase."""
        hooks = [
            HookCapability(
                id="test_hook",
                type=HookType.BEFORE,
                display_name="Test Hook",
                description="Test description",
            )
        ]
        result = _supported_hooks_to_dict(hooks)
        assert "displayName" in result[0]
        assert "display_name" not in result[0]


class TestBuildExtensionCapabilitiesWithHooks:
    """Tests for build_extension_capabilities() with hooks support."""

    def test_capability_with_empty_hooks(self):
        caps = [
            ExtensionCapability(
                display_name="Test", description="Test capability.", supported_hooks=[]
            )
        ]
        result = build_extension_capabilities(caps)
        assert result[0].params is not None
        assert result[0].params["supportedHooks"] == []

    def test_capability_with_single_hook(self):
        hooks = [
            HookCapability(
                id="before_tool_execution",
                type=HookType.BEFORE,
                display_name="Before Tool Execution",
                description="Hook that runs before tool execution",
            )
        ]
        caps = [
            ExtensionCapability(
                display_name="Test",
                description="Test capability.",
                supported_hooks=hooks,
            )
        ]
        result = build_extension_capabilities(caps)
        assert result[0].params is not None
        assert "supportedHooks" in result[0].params
        assert len(result[0].params["supportedHooks"]) == 1
        assert result[0].params["supportedHooks"][0]["id"] == "before_tool_execution"
        assert result[0].params["supportedHooks"][0]["type"] == "BEFORE"
        assert (
            result[0].params["supportedHooks"][0]["displayName"]
            == "Before Tool Execution"
        )

    def test_capability_with_multiple_hooks(self):
        hooks = [
            HookCapability(
                id="before_hook",
                type=HookType.BEFORE,
                display_name="Before Hook",
                description="Before hook description",
            ),
            HookCapability(
                id="after_hook",
                type=HookType.AFTER,
                display_name="After Hook",
                description="After hook description",
            ),
        ]
        caps = [
            ExtensionCapability(
                display_name="Test",
                description="Test capability.",
                supported_hooks=hooks,
            )
        ]
        result = build_extension_capabilities(caps)
        assert result[0].params is not None
        assert len(result[0].params["supportedHooks"]) == 2
        assert result[0].params["supportedHooks"][0]["id"] == "before_hook"
        assert result[0].params["supportedHooks"][1]["id"] == "after_hook"

    def test_full_capability_with_tools_and_hooks(self):
        """Test capability with both tools and hooks configured."""
        hooks = [
            HookCapability(
                id="onboarding_before",
                type=HookType.BEFORE,
                display_name="Onboarding Before Hook",
                description="Hook executed before onboarding workflow step.",
            )
        ]
        caps = [
            ExtensionCapability(
                id="onboarding",
                display_name="Onboarding",
                description="Onboarding workflow extensions.",
                instruction_supported=True,
                tools=Tools(additions=ToolAdditions(enabled=True)),
                supported_hooks=hooks,
            )
        ]
        result = build_extension_capabilities(caps)

        assert result[0].uri == "urn:sap:extension-capability:v1:onboarding"
        assert result[0].params is not None
        assert result[0].params["capabilityId"] == "onboarding"
        assert result[0].params["displayName"] == "Onboarding"
        assert result[0].params["instructionSupported"] is True
        assert result[0].params["tools"]["additions"]["enabled"] is True
        assert len(result[0].params["supportedHooks"]) == 1
        assert result[0].params["supportedHooks"][0]["id"] == "onboarding_before"
        assert result[0].params["supportedHooks"][0]["type"] == "BEFORE"

    def test_multiple_capabilities_with_different_hooks(self):
        """Test multiple capabilities each with different hooks."""
        caps = [
            ExtensionCapability(
                id="onboarding",
                display_name="Onboarding",
                description="Onboarding workflow.",
                supported_hooks=[
                    HookCapability(
                        id="onboarding_before",
                        type=HookType.BEFORE,
                        display_name="Onboarding Before",
                        description="Before onboarding",
                    )
                ],
            ),
            ExtensionCapability(
                id="doc-processing",
                display_name="Doc Processing",
                description="Document processing.",
                supported_hooks=[
                    HookCapability(
                        id="doc_validation",
                        type=HookType.BEFORE,
                        display_name="Doc Validation",
                        description="Validate documents",
                    ),
                    HookCapability(
                        id="doc_after",
                        type=HookType.AFTER,
                        display_name="Doc After",
                        description="After document processing",
                    ),
                ],
            ),
        ]
        result = build_extension_capabilities(caps)

        assert len(result) == 2
        assert result[0].params is not None
        assert len(result[0].params["supportedHooks"]) == 1
        assert result[0].params["supportedHooks"][0]["id"] == "onboarding_before"
        assert result[1].params is not None
        assert len(result[1].params["supportedHooks"]) == 2
        assert result[1].params["supportedHooks"][0]["id"] == "doc_validation"
        assert result[1].params["supportedHooks"][1]["id"] == "doc_after"


class TestBuildExtensionCapabilitiesExportedFromPackage:
    """Test that build_extension_capabilities is properly exported."""

    def test_importable_from_package(self):
        from sap_cloud_sdk.extensibility import build_extension_capabilities

        assert callable(build_extension_capabilities)

    def test_in_all(self):
        import sap_cloud_sdk.extensibility as ext

        assert "build_extension_capabilities" in ext.__all__
        assert "EXTENSION_CAPABILITY_SCHEMA_VERSION" in ext.__all__
