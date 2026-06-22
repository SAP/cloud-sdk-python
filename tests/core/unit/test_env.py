"""Unit tests for core.env typed environment-variable readers."""

import pytest

from sap_cloud_sdk.core.env import read_env_bool, read_env_choice, read_env_str


class TestReadEnvStr:
    def test_returns_default_when_absent(self, monkeypatch):
        monkeypatch.delenv("FOO", raising=False)
        assert read_env_str("FOO", "fallback") == "fallback"

    def test_returns_value_when_present(self, monkeypatch):
        monkeypatch.setenv("FOO", "hello")
        assert read_env_str("FOO", "fallback") == "hello"

    def test_trims_whitespace(self, monkeypatch):
        monkeypatch.setenv("FOO", "  hello  ")
        assert read_env_str("FOO", "fallback") == "hello"

    def test_empty_string_var_returns_empty_not_default(self, monkeypatch):
        """An env var set to '' is 'present' — return '', not the default.

        Pinned for callers (e.g. AICORE_FILTER_DIRECTIONS) that distinguish
        'unset' from 'explicitly cleared'.
        """
        monkeypatch.setenv("FOO", "")
        assert read_env_str("FOO", "fallback") == ""

    def test_empty_default(self, monkeypatch):
        monkeypatch.delenv("FOO", raising=False)
        assert read_env_str("FOO") == ""


class TestReadEnvBool:
    @pytest.mark.parametrize("raw", ["true", "TRUE", "True", "1", "yes", "YES"])
    def test_truthy_values(self, monkeypatch, raw):
        monkeypatch.setenv("FLAG", raw)
        assert read_env_bool("FLAG", default=False) is True

    @pytest.mark.parametrize("raw", ["false", "0", "no", "anything", ""])
    def test_falsy_values(self, monkeypatch, raw):
        monkeypatch.setenv("FLAG", raw)
        assert read_env_bool("FLAG", default=True) is False

    def test_default_when_absent(self, monkeypatch):
        monkeypatch.delenv("FLAG", raising=False)
        assert read_env_bool("FLAG", default=True) is True
        assert read_env_bool("FLAG", default=False) is False


class TestReadEnvChoice:
    def test_returns_default_when_absent(self, monkeypatch):
        monkeypatch.delenv("LEVEL", raising=False)
        assert read_env_choice("LEVEL", {0, 2, 4, 6}, default=4) == 4

    def test_returns_parsed_value_when_valid(self, monkeypatch):
        monkeypatch.setenv("LEVEL", "0")
        assert read_env_choice("LEVEL", {0, 2, 4, 6}, default=4) == 0

    def test_raises_on_value_not_in_choices(self, monkeypatch):
        monkeypatch.setenv("LEVEL", "3")
        with pytest.raises(ValueError, match="LEVEL"):
            read_env_choice("LEVEL", {0, 2, 4, 6}, default=4)

    def test_raises_on_unparseable_value(self, monkeypatch):
        monkeypatch.setenv("LEVEL", "high")
        with pytest.raises(ValueError, match="LEVEL"):
            read_env_choice("LEVEL", {0, 2, 4, 6}, default=4)

    def test_trims_whitespace_before_parsing(self, monkeypatch):
        monkeypatch.setenv("LEVEL", "  2  ")
        assert read_env_choice("LEVEL", {0, 2, 4, 6}, default=4) == 2
