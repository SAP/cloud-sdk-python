"""Unit tests for orchestration._models."""

import os
import pytest
from unittest.mock import patch

from sap_cloud_sdk.orchestration._models import (
    ContentFilterConfig,
    FilteringModuleConfig,
    PromptShieldConfig,
)


class TestContentFilterConfig:
    def test_defaults(self):
        cfg = ContentFilterConfig()
        assert cfg.hate == 4
        assert cfg.violence == 4
        assert cfg.sexual == 4
        assert cfg.self_harm == 4

    def test_custom_values(self):
        cfg = ContentFilterConfig(hate=0, violence=2, sexual=6, self_harm=0)
        assert cfg.hate == 0
        assert cfg.violence == 2
        assert cfg.sexual == 6
        assert cfg.self_harm == 0


class TestFilteringModuleConfigToDict:
    def test_default_config_produces_both_directions(self):
        result = FilteringModuleConfig().to_dict()
        assert "input" in result
        assert "output" in result

    def test_input_filter_has_azure_type(self):
        result = FilteringModuleConfig().to_dict()
        f = result["input"]["filters"][0]
        assert f["type"] == "azure_content_safety"

    def test_default_thresholds_are_4(self):
        result = FilteringModuleConfig().to_dict()
        cfg = result["input"]["filters"][0]["config"]
        assert cfg["hate"] == 4
        assert cfg["violence"] == 4
        assert cfg["sexual"] == 4
        assert cfg["self_harm"] == 4

    def test_prompt_shield_on_input_only(self):
        result = FilteringModuleConfig().to_dict()
        in_cfg = result["input"]["filters"][0]["config"]
        out_cfg = result["output"]["filters"][0]["config"]
        assert in_cfg.get("prompt_shield") is True
        assert "prompt_shield" not in out_cfg

    def test_severity_zero_serialized_not_omitted(self):
        cfg = FilteringModuleConfig(
            input_filter=ContentFilterConfig(hate=0, violence=0, sexual=0, self_harm=0),
            output_filter=None,
        )
        result = cfg.to_dict()
        in_cfg = result["input"]["filters"][0]["config"]
        assert in_cfg["hate"] == 0
        assert in_cfg["violence"] == 0

    def test_none_input_filter_omits_input_key(self):
        cfg = FilteringModuleConfig(input_filter=None, output_filter=ContentFilterConfig())
        result = cfg.to_dict()
        assert "input" not in result
        assert "output" in result

    def test_none_output_filter_omits_output_key(self):
        cfg = FilteringModuleConfig(input_filter=ContentFilterConfig(), output_filter=None)
        result = cfg.to_dict()
        assert "input" in result
        assert "output" not in result

    def test_no_prompt_shield_when_disabled(self):
        cfg = FilteringModuleConfig(
            prompt_shield=PromptShieldConfig(enabled=False)
        )
        result = cfg.to_dict()
        in_cfg = result["input"]["filters"][0]["config"]
        assert "prompt_shield" not in in_cfg

    def test_no_prompt_shield_when_none(self):
        cfg = FilteringModuleConfig(prompt_shield=None)
        result = cfg.to_dict()
        in_cfg = result["input"]["filters"][0]["config"]
        assert "prompt_shield" not in in_cfg

    def test_empty_dict_when_both_filters_none(self):
        cfg = FilteringModuleConfig(input_filter=None, output_filter=None)
        assert cfg.to_dict() == {}


class TestFilteringModuleConfigFromEnv:
    def _clear_env(self, monkeypatch):
        for k in list(os.environ):
            if k.startswith("ORCH_FILTER"):
                monkeypatch.delenv(k, raising=False)

    def test_defaults_with_no_env(self, monkeypatch):
        self._clear_env(monkeypatch)
        cfg = FilteringModuleConfig.from_env()
        assert cfg is not None
        assert cfg.input_filter is not None
        assert cfg.output_filter is not None
        assert cfg.input_filter.hate == 4

    def test_disabled_returns_none(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("ORCH_FILTER_ENABLED", "false")
        assert FilteringModuleConfig.from_env() is None

    def test_custom_severity_from_env(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("ORCH_FILTER_SELF_HARM", "0")
        monkeypatch.setenv("ORCH_FILTER_HATE", "2")
        cfg = FilteringModuleConfig.from_env()
        assert cfg.input_filter.self_harm == 0
        assert cfg.input_filter.hate == 2

    def test_input_only_direction(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("ORCH_FILTER_DIRECTIONS", "input")
        cfg = FilteringModuleConfig.from_env()
        assert cfg.input_filter is not None
        assert cfg.output_filter is None

    def test_output_only_direction(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("ORCH_FILTER_DIRECTIONS", "output")
        cfg = FilteringModuleConfig.from_env()
        assert cfg.input_filter is None
        assert cfg.output_filter is not None
        assert cfg.prompt_shield is None  # prompt_shield is input-only

    def test_prompt_shield_false_from_env(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("ORCH_FILTER_PROMPT_SHIELD", "false")
        cfg = FilteringModuleConfig.from_env()
        assert cfg.prompt_shield.enabled is False

    def test_invalid_severity_raises(self, monkeypatch):
        self._clear_env(monkeypatch)
        monkeypatch.setenv("ORCH_FILTER_HATE", "3")
        with pytest.raises(ValueError, match="ORCH_FILTER_HATE"):
            FilteringModuleConfig.from_env()
