"""Unit tests for orchestration.set_filtering()."""

import os
import pytest
import litellm

from sap_cloud_sdk.orchestration import set_filtering
from sap_cloud_sdk.orchestration._litellm_patch import (
    FilteringOrchestrationConfig,
    _ORIGINAL_CONFIG,
    _install,
)
from sap_cloud_sdk.orchestration._models import FilteringModuleConfig


@pytest.fixture(autouse=True)
def restore_litellm():
    """Restore litellm config after each test."""
    yield
    _install(None)


def _clear_orch_env(monkeypatch):
    for k in list(os.environ):
        if k.startswith("ORCH_FILTER"):
            monkeypatch.delenv(k, raising=False)


class TestSetFiltering:
    def test_patches_litellm(self, monkeypatch):
        _clear_orch_env(monkeypatch)
        set_filtering()
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig

    def test_disable_restores_original(self, monkeypatch):
        _clear_orch_env(monkeypatch)
        set_filtering()
        set_filtering(enabled=False)
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_override_self_harm_threshold(self, monkeypatch):
        _clear_orch_env(monkeypatch)
        set_filtering(self_harm=0)
        # Access the active config via the module-level variable
        from sap_cloud_sdk.orchestration import _litellm_patch
        assert _litellm_patch._active_cfg.input_filter.self_harm == 0

    def test_other_thresholds_unchanged_on_partial_override(self, monkeypatch):
        _clear_orch_env(monkeypatch)
        set_filtering(self_harm=0)
        from sap_cloud_sdk.orchestration import _litellm_patch
        assert _litellm_patch._active_cfg.input_filter.hate == 4   # default preserved

    def test_idempotent(self, monkeypatch):
        _clear_orch_env(monkeypatch)
        set_filtering()
        set_filtering()
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig

    def test_env_disabled_before_set_filtering(self, monkeypatch):
        _clear_orch_env(monkeypatch)
        monkeypatch.setenv("ORCH_FILTER_ENABLED", "false")
        set_filtering()   # should still be disabled since env says no
        # env is read inside from_env(); set_filtering() with no args reads env
        from sap_cloud_sdk.orchestration import _litellm_patch
        assert _litellm_patch._active_cfg is None

    def test_explicit_threshold_ignores_enabled_false_env(self, monkeypatch):
        _clear_orch_env(monkeypatch)
        # Even with ORCH_FILTER_ENABLED=false, explicit thresholds passed to
        # set_filtering() should activate filtering (programmatic override wins).
        monkeypatch.setenv("ORCH_FILTER_ENABLED", "false")
        set_filtering(self_harm=2)  # explicit arg → activates filtering
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig
