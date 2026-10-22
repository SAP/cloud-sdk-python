"""Unit tests for aicore.filtering set_filtering / disable_filtering."""

import os

import litellm
import pytest

from sap_cloud_sdk.aicore.filtering import (
    AzureContentFilter,
    ContentFiltering,
    InputFiltering,
    Severity,
    disable_filtering,
    set_filtering,
)
from sap_cloud_sdk.aicore.filtering._patch import (
    _ORIGINAL_CONFIG,
    FilteringOrchestrationConfig,
    _install,
)


@pytest.fixture(autouse=True)
def restore_litellm():
    """Restore litellm config after each test."""
    yield
    _install(None)


def _clear_aicore_env(monkeypatch):
    for k in list(os.environ):
        if k.startswith("AICORE_FILTER"):
            monkeypatch.delenv(k, raising=False)


class TestSetFiltering:
    def test_no_args_applies_env_defaults(self, monkeypatch):
        """set_filtering() with no args reads AICORE_FILTER_* and installs."""
        _clear_aicore_env(monkeypatch)
        set_filtering()
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig

    def test_explicit_none_applies_env_defaults(self, monkeypatch):
        """set_filtering(None) is equivalent to set_filtering()."""
        _clear_aicore_env(monkeypatch)
        set_filtering(None)
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig

    def test_install_with_content_filtering_object(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        cfg = ContentFiltering(
            input_filtering=InputFiltering(
                filters=[AzureContentFilter(self_harm=Severity.STRICT)]
            )
        )
        set_filtering(cfg)
        from sap_cloud_sdk.aicore.filtering import _patch as _filters_mod

        active = _filters_mod._active_cfg
        assert active is not None
        assert active.input_filtering.filters[0].config["self_harm"] == 0

    def test_idempotent(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        set_filtering()
        set_filtering()
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig

    def test_env_disabled_set_filtering_stays_disabled(self, monkeypatch):
        """AICORE_FILTER_ENABLED=false + set_filtering() → filter stays off."""
        _clear_aicore_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_ENABLED", "false")
        set_filtering()
        from sap_cloud_sdk.aicore.filtering import _patch as _filters_mod

        assert _filters_mod._active_cfg is None

    def test_explicit_config_ignores_enabled_false_env(self, monkeypatch):
        # Policy: an explicit ContentFiltering object always activates filtering,
        # even when AICORE_FILTER_ENABLED=false would disable env-driven setup.
        # Passing a non-None config is an explicit override.
        _clear_aicore_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_ENABLED", "false")
        set_filtering(
            ContentFiltering(
                input_filtering=InputFiltering(filters=[AzureContentFilter()])
            )
        )
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig

    def test_multi_filter_input(self, monkeypatch):
        """InputFiltering can carry multiple filter providers in order."""
        from sap_cloud_sdk.aicore.filtering import LlamaGuard38bFilter

        _clear_aicore_env(monkeypatch)
        cfg = ContentFiltering(
            input_filtering=InputFiltering(
                filters=[
                    AzureContentFilter(),
                    LlamaGuard38bFilter(hate=True),
                ]
            )
        )
        set_filtering(cfg)
        from sap_cloud_sdk.aicore.filtering import _patch as _filters_mod

        filters = _filters_mod._active_cfg.input_filtering.filters
        assert len(filters) == 2
        assert filters[0].provider == "azure_content_safety"
        assert filters[1].provider == "llama_guard_3_8b"


class TestDisableFiltering:
    def test_disable_restores_original_config(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        set_filtering()
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig
        disable_filtering()
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_disable_is_idempotent(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        disable_filtering()
        disable_filtering()
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_disable_when_never_enabled(self, monkeypatch):
        # disable_filtering() before any set_filtering() is a clean no-op:
        # litellm config stays at the original AND _active_cfg stays cleared.
        _clear_aicore_env(monkeypatch)
        from sap_cloud_sdk.aicore.filtering import _patch as _filters_mod

        disable_filtering()
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG
        assert _filters_mod._active_cfg is None


class TestTransformRequestMultiModule:
    """Regression tests: filtering must be injected into every fallback module, not just modules[0]."""

    def _make_cfg(self) -> ContentFiltering:
        return ContentFiltering(
            input_filtering=InputFiltering(filters=[AzureContentFilter()])
        )

    def _call_transform_request(self, modules_value):
        """Call the filtering injection logic directly, bypassing the LiteLLM base class."""
        from unittest.mock import patch

        body = {"config": {"modules": modules_value}}
        instance = FilteringOrchestrationConfig()

        with patch(
            "sap_cloud_sdk.aicore.filtering._patch.GenAIHubOrchestrationConfig.transform_request",
            return_value=body,
        ):
            return instance.transform_request(
                model="sap/x",
                messages=[],
                optional_params={},
                litellm_params={},
                headers={},
            )

    def test_single_module_dict_gets_filtering(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        set_filtering(self._make_cfg())
        modules = {"model_id": "primary-llm"}
        result = self._call_transform_request(modules)
        assert "filtering" in result["config"]["modules"]

    def test_multi_module_list_all_get_filtering(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        set_filtering(self._make_cfg())
        modules = [
            {"model_id": "primary-llm"},
            {"model_id": "fallback-llm-1"},
            {"model_id": "fallback-llm-2"},
        ]
        result = self._call_transform_request(modules)
        for i, m in enumerate(result["config"]["modules"]):
            assert "filtering" in m, f"modules[{i}] missing filtering block"

    def test_multi_module_filtering_dict_is_identical_across_modules(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        set_filtering(self._make_cfg())
        modules = [{"model_id": "a"}, {"model_id": "b"}]
        result = self._call_transform_request(modules)
        assert (
            result["config"]["modules"][0]["filtering"]
            == result["config"]["modules"][1]["filtering"]
        )
