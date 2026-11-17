"""Tests for HookShortCircuit exception."""

import pytest

from sap_cloud_sdk.extensibility.exceptions import (
    ExtensibilityError,
    HookShortCircuit,
)


class TestHookShortCircuitHierarchy:
    def test_is_extensibility_error(self):
        exc = HookShortCircuit("blocked")
        assert isinstance(exc, ExtensibilityError)

    def test_is_exception(self):
        exc = HookShortCircuit("blocked")
        assert isinstance(exc, Exception)

    def test_caught_by_base(self):
        with pytest.raises(ExtensibilityError):
            raise HookShortCircuit("blocked")


class TestHookShortCircuitFields:
    def test_reason_set(self):
        exc = HookShortCircuit("blocked by hook")
        assert exc.reason == "blocked by hook"

    def test_str_is_reason(self):
        exc = HookShortCircuit("blocked by hook")
        assert str(exc) == "blocked by hook"

    def test_hook_name_default_empty(self):
        exc = HookShortCircuit("blocked")
        assert exc.hook_name == ""

    def test_capability_id_default_empty(self):
        exc = HookShortCircuit("blocked")
        assert exc.capability_id == ""

    def test_hook_name_set(self):
        exc = HookShortCircuit("blocked", hook_name="my-hook")
        assert exc.hook_name == "my-hook"

    def test_capability_id_set(self):
        exc = HookShortCircuit("blocked", capability_id="my-cap")
        assert exc.capability_id == "my-cap"

    def test_all_fields(self):
        exc = HookShortCircuit(
            "hook refused", hook_name="guard", capability_id="default"
        )
        assert exc.reason == "hook refused"
        assert exc.hook_name == "guard"
        assert exc.capability_id == "default"

    def test_raise_and_catch_preserves_fields(self):
        try:
            raise HookShortCircuit("stop", hook_name="h1", capability_id="cap1")
        except HookShortCircuit as exc:
            assert exc.hook_name == "h1"
            assert exc.capability_id == "cap1"
