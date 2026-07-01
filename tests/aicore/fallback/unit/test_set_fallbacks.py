"""Unit tests for :func:`set_fallbacks` lifecycle and env-driven activation."""

from __future__ import annotations

import os

import litellm
import pytest

from sap_cloud_sdk.aicore.fallback import _patch as _fallback_patch
from sap_cloud_sdk.aicore.fallback._patch import (
    OrchestrationPatchConfig,
    _install_fallback,
)
from sap_cloud_sdk.aicore.fallback.fallback import (
    FallbackConfig,
    FallbackModel,
    set_fallbacks,
)
from sap_cloud_sdk.aicore.filtering._patch import (
    _ORIGINAL_CONFIG,
    _install as _install_filter,
)


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Clear env and patch state before/after each test."""
    for key in list(os.environ):
        if key.startswith("AICORE_FALLBACK"):
            monkeypatch.delenv(key, raising=False)
    _install_filter(None)
    _install_fallback(None)
    yield
    _install_filter(None)
    _install_fallback(None)


class TestSetFallbacks:
    def test_with_explicit_config_installs_patch(self):
        set_fallbacks(FallbackConfig([FallbackModel(model="sap/x")]))
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig
        assert _fallback_patch._active_fallback_cfg is not None

    def test_with_none_no_env_clears(self):
        set_fallbacks(FallbackConfig([FallbackModel(model="sap/x")]))
        set_fallbacks(None)
        assert _fallback_patch._active_fallback_cfg is None
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_with_none_reads_env_when_enabled(self, monkeypatch):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "true")
        monkeypatch.setenv("AICORE_FALLBACK_MODELS", "sap/a,sap/b")
        set_fallbacks(None)
        assert _fallback_patch._active_fallback_cfg is not None
        assert [m.model for m in _fallback_patch._active_fallback_cfg.models] == [
            "sap/a",
            "sap/b",
        ]
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig

    def test_with_none_env_disabled_keeps_inactive(self):
        # AICORE_FALLBACK_ENABLED unset → from_env returns None → install None.
        set_fallbacks(None)
        assert _fallback_patch._active_fallback_cfg is None
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_idempotent(self):
        cfg = FallbackConfig([FallbackModel(model="sap/x")])
        set_fallbacks(cfg)
        set_fallbacks(cfg)
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig
