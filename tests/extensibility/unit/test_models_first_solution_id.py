"""Tests for ExtensionCapabilityImplementation.first_solution_id."""

from sap_cloud_sdk.extensibility._models import (
    ExtensionCapabilityImplementation,
    ExtensionSourceInfo,
    ExtensionSourceMapping,
)


def _make_source_info(solution_id: str = "") -> ExtensionSourceInfo:
    return ExtensionSourceInfo(
        extension_name="ext",
        extension_version="1.0",
        extension_id="ext-id",
        solution_id=solution_id,
    )


class TestFirstSolutionIdEmpty:
    def test_no_source(self):
        impl = ExtensionCapabilityImplementation(capability_id="default")
        assert impl.first_solution_id == ""

    def test_source_empty_maps(self):
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(tools={}, hooks={}, instructions={}),
        )
        assert impl.first_solution_id == ""

    def test_source_items_without_solution_id(self):
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={"t1": _make_source_info("")},
                hooks={},
                instructions={},
            ),
        )
        assert impl.first_solution_id == ""


class TestFirstSolutionIdFound:
    def test_from_instructions(self):
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={},
                hooks={},
                instructions={"ext-1": _make_source_info("sol-abc")},
            ),
        )
        assert impl.first_solution_id == "sol-abc"

    def test_from_hooks_when_no_instructions(self):
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={},
                hooks={"hook-1": _make_source_info("sol-hook")},
                instructions={},
            ),
        )
        assert impl.first_solution_id == "sol-hook"

    def test_from_tools_when_no_instructions_or_hooks(self):
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={"tool-1": _make_source_info("sol-tool")},
                hooks={},
                instructions={},
            ),
        )
        assert impl.first_solution_id == "sol-tool"

    def test_instructions_take_priority_over_hooks(self):
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={},
                hooks={"hook-1": _make_source_info("sol-hook")},
                instructions={"ext-1": _make_source_info("sol-instr")},
            ),
        )
        assert impl.first_solution_id == "sol-instr"

    def test_returns_first_non_empty(self):
        impl = ExtensionCapabilityImplementation(
            capability_id="default",
            source=ExtensionSourceMapping(
                tools={},
                hooks={},
                instructions={
                    "ext-empty": _make_source_info(""),
                    "ext-full": _make_source_info("sol-second"),
                },
            ),
        )
        assert impl.first_solution_id == "sol-second"
