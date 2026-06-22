"""Unit tests for aicore.filtering set_filtering / disable_filtering."""

import os
import pytest
import litellm

from sap_cloud_sdk.aicore.filtering import disable_filtering, set_filtering
from sap_cloud_sdk.aicore.filtering._litellm_patch import (
    FilteringOrchestrationConfig,
    _ORIGINAL_CONFIG,
    _install,
)
from sap_cloud_sdk.aicore.filtering._models import (
    Severity,
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
    def test_patches_litellm(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        set_filtering()
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig

    def test_override_self_harm_threshold(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        set_filtering(self_harm=Severity.STRICT)
        from sap_cloud_sdk.aicore.filtering import _litellm_patch

        assert _litellm_patch._active_cfg.input_filter.self_harm == Severity.STRICT

    def test_other_thresholds_unchanged_on_partial_override(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        set_filtering(self_harm=Severity.STRICT)
        from sap_cloud_sdk.aicore.filtering import _litellm_patch

        assert _litellm_patch._active_cfg.input_filter.hate == Severity.MEDIUM

    def test_idempotent(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        set_filtering()
        set_filtering()
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig

    def test_env_disabled_before_set_filtering(self, monkeypatch):
        _clear_aicore_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_ENABLED", "false")
        set_filtering()  # should stay disabled — env says no
        from sap_cloud_sdk.aicore.filtering import _litellm_patch

        assert _litellm_patch._active_cfg is None

    def test_explicit_threshold_ignores_enabled_false_env(self, monkeypatch):
        # Policy: explicit programmatic thresholds always activate filtering,
        # even when AICORE_FILTER_ENABLED=false disables it at the env level.
        # This lets callers override an env-disabled default without changing
        # env vars (e.g. tightening a single category at runtime).
        _clear_aicore_env(monkeypatch)
        monkeypatch.setenv("AICORE_FILTER_ENABLED", "false")
        set_filtering(self_harm=Severity.LOW)
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig


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
        # disable_filtering() before any set_filtering() should be a clean
        # no-op: litellm config stays at the original AND the module-level
        # _active_cfg stays cleared (no partial state from a previous run).
        _clear_aicore_env(monkeypatch)
        from sap_cloud_sdk.aicore.filtering import _litellm_patch

        disable_filtering()
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG
        assert _litellm_patch._active_cfg is None
