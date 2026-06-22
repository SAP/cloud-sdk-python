"""Unit tests for aicore.filtering._models — Severity enum only.

Container and provider dataclasses have moved:
- ContentFilterConfig / PromptShieldConfig / FilteringModuleConfig were
  replaced by ContentFiltering / InputFiltering / OutputFiltering /
  AzureContentFilter — see test_modules.py and test_filters.py.
"""

from sap_cloud_sdk.aicore.filtering._models import Severity


class TestSeverity:
    def test_values(self):
        assert Severity.STRICT == 0
        assert Severity.LOW == 2
        assert Severity.MEDIUM == 4
        assert Severity.OFF == 6

    def test_int_enum_serialises_as_int(self):
        """IntEnum members compare equal to and serialise as their int value."""
        assert Severity.STRICT == 0
        assert int(Severity.MEDIUM) == 4

    def test_member_count(self):
        assert len(Severity) == 4
