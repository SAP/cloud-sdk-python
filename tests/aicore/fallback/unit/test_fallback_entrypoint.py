"""Unit tests for fallback activation (``_apply_fallback``) and
``disable_fallbacks`` lifecycle, including env-driven activation.

Activation is wired into ``set_aicore_config(fallback=...)`` in production; the
underlying installer is ``_apply_fallback`` and the public clear is
``disable_fallbacks``. These tests drive those directly to avoid mocking
credential loading.
"""

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
    _apply_fallback,
    disable_fallbacks,
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


class TestApplyFallback:
    def test_with_explicit_config_installs_patch(self):
        _apply_fallback(FallbackConfig([FallbackModel(model="sap/x")]))
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig
        assert _fallback_patch._active_fallback_cfg is not None

    def test_with_none_reads_env_when_enabled(self, monkeypatch):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "true")
        monkeypatch.setenv("AICORE_FALLBACK_MODELS", "sap/a,sap/b")
        _apply_fallback(None)
        assert _fallback_patch._active_fallback_cfg is not None
        assert [m.model for m in _fallback_patch._active_fallback_cfg.models] == [
            "sap/a",
            "sap/b",
        ]
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig

    def test_with_none_env_disabled_keeps_inactive(self):
        # AICORE_FALLBACK_ENABLED unset → from_env returns None → install None.
        _apply_fallback(None)
        assert _fallback_patch._active_fallback_cfg is None
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_idempotent(self):
        cfg = FallbackConfig([FallbackModel(model="sap/x")])
        _apply_fallback(cfg)
        _apply_fallback(cfg)
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig


class TestDisableFallbacks:
    def test_clears_installed_config(self):
        _apply_fallback(FallbackConfig([FallbackModel(model="sap/x")]))
        disable_fallbacks()
        assert _fallback_patch._active_fallback_cfg is None
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_idempotent_when_already_disabled(self):
        disable_fallbacks()
        disable_fallbacks()
        assert _fallback_patch._active_fallback_cfg is None
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG
