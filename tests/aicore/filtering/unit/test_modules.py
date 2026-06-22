"""Unit tests for aicore.filtering._modules direction containers + ContentFiltering."""

import os

import pytest

from sap_cloud_sdk.aicore.filtering._filters import (
    AzureContentFilter,
    LlamaGuard38bFilter,
)
from sap_cloud_sdk.aicore.filtering._modules import (
    ContentFiltering,
    InputFiltering,
    OutputFiltering,
)


class TestInputFiltering:
    def test_empty_filter_list(self):
        assert InputFiltering(filters=[]).to_dict() == {"filters": []}

    def test_single_filter(self):
        d = InputFiltering(filters=[AzureContentFilter()]).to_dict()
        assert d == {
            "filters": [
                {
                    "type": "azure_content_safety",
                    "config": {"hate": 4, "violence": 4, "sexual": 4, "self_harm": 4},
                }
            ]
        }

    def test_multiple_filters_order_preserved(self):
        d = InputFiltering(
            filters=[AzureContentFilter(), LlamaGuard38bFilter()]
        ).to_dict()
        assert [f["type"] for f in d["filters"]] == [
            "azure_content_safety",
            "llama_guard_3_8b",
        ]


class TestOutputFiltering:
    def test_filters_only(self):
        d = OutputFiltering(filters=[AzureContentFilter()]).to_dict()
        assert "filters" in d
        assert "stream_options" not in d

    def test_with_stream_options(self):
        d = OutputFiltering(
            filters=[AzureContentFilter()], stream_options={"chunk_size": 100}
        ).to_dict()
        assert d["stream_options"] == {"chunk_size": 100}

    def test_stream_options_none_omits_key(self):
        d = OutputFiltering(
            filters=[AzureContentFilter()], stream_options=None
        ).to_dict()
        assert "stream_options" not in d


class TestContentFiltering:
    def test_both_none_returns_empty_dict(self):
        assert ContentFiltering().to_dict() == {}

    def test_input_only(self):
        cfg = ContentFiltering(
            input_filtering=InputFiltering(filters=[AzureContentFilter()])
        )
        d = cfg.to_dict()
        assert "input" in d
        assert "output" not in d

    def test_output_only(self):
        cfg = ContentFiltering(
            output_filtering=OutputFiltering(filters=[AzureContentFilter()])
        )
        d = cfg.to_dict()
        assert "output" in d
        assert "input" not in d

    def test_both_present(self):
        cfg = ContentFiltering(
            input_filtering=InputFiltering(filters=[AzureContentFilter()]),
            output_filtering=OutputFiltering(filters=[AzureContentFilter()]),
        )
        d = cfg.to_dict()
        assert "input" in d
        assert "output" in d


class TestContentFilteringFromEnv:
    def _clear_env(self, monkeypatch):
        for k in list(os.environ):
            if k.startswith("AICORE_FILTER"):
                monkeypatch.delenv(k, raising=False)

    def test_defaults_with_no_env(self, monkeypatch):
        self._clear_env(monkeypatch)
        cfg = ContentFiltering.from_env()
        assert cfg is not None
        assert cfg.input_filtering is not None
        assert cfg.output_filtering is not None
        # Default policy: one AzureContentFilter per direction at MEDIUM,
        # prompt_shield True on input only.
        in_filter = cfg.input_filtering.filters[0]
        assert isinstance(in_filter, AzureContentFilter)
        assert in_filter.config["hate"] == 4
        assert in_filter.config.get("prompt_shield") is True
        out_filter = cfg.output_filtering.filters[0]
        assert "prompt_shield" not in out_filter.config

    def test_disabled_returns_none(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_ENABLED", "false")
        assert ContentFiltering.from_env() is None

    def test_custom_severity_from_env(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_SELF_HARM", "0")
        monkeypatch.setenv("AICORE_FILTER_HATE", "2")
        cfg = ContentFiltering.from_env()
        assert cfg is not None
        in_filter = cfg.input_filtering.filters[0]
        assert in_filter.config["self_harm"] == 0
        assert in_filter.config["hate"] == 2

    def test_input_only_direction(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_DIRECTIONS", "input")
        cfg = ContentFiltering.from_env()
        assert cfg is not None
        assert cfg.input_filtering is not None
        assert cfg.output_filtering is None

    def test_output_only_direction(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_DIRECTIONS", "output")
        cfg = ContentFiltering.from_env()
        assert cfg is not None
        assert cfg.input_filtering is None
        assert cfg.output_filtering is not None

    def test_prompt_shield_false_from_env(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_PROMPT_SHIELD", "false")
        cfg = ContentFiltering.from_env()
        assert cfg is not None
        in_filter = cfg.input_filtering.filters[0]
        assert "prompt_shield" not in in_filter.config

    def test_invalid_severity_raises(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_HATE", "3")
        with pytest.raises(ValueError, match="AICORE_FILTER_HATE"):
            ContentFiltering.from_env()

    def test_directions_empty_string_disables_both(self, monkeypatch):
        """AICORE_FILTER_DIRECTIONS='' splits to empty set → neither direction."""
        self._clear_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_DIRECTIONS", "")
        cfg = ContentFiltering.from_env()
        assert cfg is not None
        assert cfg.input_filtering is None
        assert cfg.output_filtering is None
