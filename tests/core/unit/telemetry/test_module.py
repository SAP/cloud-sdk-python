"""Tests for Module enum."""

import pytest

from cloud_sdk_python.core.telemetry.module import Module


class TestModule:
    """Test suite for Module enum."""

    def test_module_values(self):
        """Test that Module enum has expected values."""
        assert Module.AICORE.value == "aicore"
        assert Module.AUDITLOG.value == "auditlog"
        assert Module.DESTINATION.value == "destination"
        assert Module.OBJECTSTORE.value == "objectstore"

    def test_module_str_representation(self):
        """Test that Module enum converts to string correctly."""
        assert str(Module.AICORE) == "aicore"
        assert str(Module.AUDITLOG) == "auditlog"
        assert str(Module.DESTINATION) == "destination"
        assert str(Module.OBJECTSTORE) == "objectstore"

    def test_module_is_string_enum(self):
        """Test that Module enum inherits from str."""
        assert isinstance(Module.AICORE, str)
        assert isinstance(Module.AUDITLOG, str)
        assert isinstance(Module.DESTINATION, str)

    def test_module_equality(self):
        """Test Module enum equality comparisons."""
        assert Module.AICORE == Module.AICORE
        assert Module.AICORE != Module.AUDITLOG
        assert Module.AICORE == "aicore"
        assert "aicore" == Module.AICORE

    def test_module_in_collection(self):
        """Test Module enum membership in collections."""
        modules = [Module.AICORE, Module.AUDITLOG]
        assert Module.AICORE in modules
        assert Module.DESTINATION not in modules

    def test_all_modules_present(self):
        """Test that all expected modules are present."""
        all_modules = list(Module)
        assert len(all_modules) == 4
        assert Module.AICORE in all_modules
        assert Module.AUDITLOG in all_modules
        assert Module.DESTINATION in all_modules
        assert Module.OBJECTSTORE in all_modules

    def test_module_iteration(self):
        """Test iterating over Module enum."""
        module_values = [str(m) for m in Module]
        assert "aicore" in module_values
        assert "auditlog" in module_values
        assert "destination" in module_values
        assert "objectstore" in module_values