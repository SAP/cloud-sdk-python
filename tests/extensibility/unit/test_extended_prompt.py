"""Tests for ExtensibilityClient.get_extended_instruction and get_extended_system_prompt."""

from unittest.mock import MagicMock

from sap_cloud_sdk.extensibility._models import (
    DEFAULT_EXTENSION_CAPABILITY_ID,
    ExtensionCapabilityImplementation,
)
from sap_cloud_sdk.extensibility.client import (
    ExtensibilityClient,
    _DEFAULT_INSTRUCTION_WRAPPER,
)


def _make_client(
    instruction: str | None = None,
) -> tuple[ExtensibilityClient, MagicMock]:
    transport = MagicMock()
    transport.get_extension_capability_implementation.return_value = (
        ExtensionCapabilityImplementation(
            capability_id=DEFAULT_EXTENSION_CAPABILITY_ID,
            instruction=instruction,
        )
    )
    return ExtensibilityClient(transport), transport


class TestGetExtendedInstruction:
    def test_returns_instruction_when_present(self):
        client, _ = _make_client(instruction="Do extra things.")
        assert client.get_extended_instruction(tenant="t-1") == "Do extra things."

    def test_returns_empty_string_when_no_instruction(self):
        client, _ = _make_client(instruction=None)
        assert client.get_extended_instruction(tenant="t-1") == ""

    def test_passes_tenant_to_transport(self):
        client, transport = _make_client()
        client.get_extended_instruction(tenant="tenant-abc")
        transport.get_extension_capability_implementation.assert_called_once_with(
            capability_id=DEFAULT_EXTENSION_CAPABILITY_ID,
            skip_cache=False,
            tenant="tenant-abc",
        )

    def test_passes_custom_capability_id(self):
        client, transport = _make_client()
        client.get_extended_instruction(tenant="t-1", capability_id="custom-cap")
        transport.get_extension_capability_implementation.assert_called_once_with(
            capability_id="custom-cap",
            skip_cache=False,
            tenant="t-1",
        )


class TestGetExtendedSystemPrompt:
    def test_returns_base_prompt_unchanged_when_no_instruction(self):
        client, _ = _make_client(instruction=None)
        result = client.get_extended_system_prompt("Base prompt.", tenant="t-1")
        assert result == "Base prompt."

    def test_appends_instruction_with_default_wrapper(self):
        client, _ = _make_client(instruction="Follow these rules.")
        result = client.get_extended_system_prompt("Base.", tenant="t-1")
        assert result.startswith("Base.")
        assert _DEFAULT_INSTRUCTION_WRAPPER in result
        assert "## Extended Instructions\n" in result
        assert result.endswith("Follow these rules.")

    def test_structure_with_default_wrapper(self):
        client, _ = _make_client(instruction="Extra rules.")
        result = client.get_extended_system_prompt("Base.", tenant="t-1")
        expected = (
            "Base."
            + "\n\n"
            + _DEFAULT_INSTRUCTION_WRAPPER
            + "\n\n## Extended Instructions\n"
            + "Extra rules."
        )
        assert result == expected

    def test_custom_wrapper_replaces_default(self):
        client, _ = _make_client(instruction="Extra rules.")
        result = client.get_extended_system_prompt(
            "Base.", tenant="t-1", wrapper="Custom preamble."
        )
        assert "Custom preamble." in result
        assert _DEFAULT_INSTRUCTION_WRAPPER not in result
        assert result.endswith("Extra rules.")

    def test_empty_wrapper_suppresses_preamble(self):
        client, _ = _make_client(instruction="Extra rules.")
        result = client.get_extended_system_prompt("Base.", tenant="t-1", wrapper="")
        assert result == "Base.\n\n## Extended Instructions\nExtra rules."
        assert _DEFAULT_INSTRUCTION_WRAPPER not in result

    def test_passes_tenant_to_transport(self):
        client, transport = _make_client(instruction=None)
        client.get_extended_system_prompt("Base.", tenant="tenant-xyz")
        transport.get_extension_capability_implementation.assert_called_once_with(
            capability_id=DEFAULT_EXTENSION_CAPABILITY_ID,
            skip_cache=False,
            tenant="tenant-xyz",
        )

    def test_empty_instruction_returns_base_prompt_unchanged(self):
        client, _ = _make_client(instruction="")
        result = client.get_extended_system_prompt("Base.", tenant="t-1")
        assert result == "Base."
