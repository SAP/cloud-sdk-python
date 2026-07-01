"""Unit tests for FallbackModel, FallbackConfig, and FallbackConfig.from_env."""

from __future__ import annotations

import logging
import os

import pytest

from sap_cloud_sdk.aicore.fallback.fallback import FallbackConfig, FallbackModel


# ---------------------------------------------------------------------------
# FallbackModel
# ---------------------------------------------------------------------------


class TestFallbackModelToDict:
    def test_to_dict_minimal_has_only_model(self):
        m = FallbackModel(model="sap/x")
        assert m.to_dict() == {"model": "sap/x"}

    def test_to_dict_with_params_merges_them(self):
        m = FallbackModel(model="sap/x", params={"temperature": 0.7, "max_tokens": 300})
        assert m.to_dict() == {
            "model": "sap/x",
            "temperature": 0.7,
            "max_tokens": 300,
        }

    def test_to_dict_with_model_version_includes_key(self):
        m = FallbackModel(model="sap/x", model_version="v2")
        assert m.to_dict() == {"model": "sap/x", "model_version": "v2"}

    def test_to_dict_with_empty_params_omits_them(self):
        m = FallbackModel(model="sap/x", params={})
        assert m.to_dict() == {"model": "sap/x"}

    def test_to_dict_all_fields_set(self):
        m = FallbackModel(
            model="sap/x",
            params={"temperature": 0.5},
            model_version="v3",
        )
        assert m.to_dict() == {
            "model": "sap/x",
            "model_version": "v3",
            "temperature": 0.5,
        }


# ---------------------------------------------------------------------------
# FallbackConfig
# ---------------------------------------------------------------------------


class TestFallbackConfigToLitellmKwarg:
    def test_preserves_order(self):
        cfg = FallbackConfig(
            [
                FallbackModel(model="sap/a"),
                FallbackModel(model="sap/b"),
                FallbackModel(model="sap/c"),
            ]
        )
        assert [m["model"] for m in cfg.to_litellm_kwarg()] == [
            "sap/a",
            "sap/b",
            "sap/c",
        ]

    def test_empty_list_returns_empty(self):
        cfg = FallbackConfig([])
        assert cfg.to_litellm_kwarg() == []

    def test_default_factory_produces_empty_list(self):
        cfg = FallbackConfig()
        assert cfg.models == []
        assert cfg.to_litellm_kwarg() == []

    def test_per_model_params_propagated(self):
        cfg = FallbackConfig(
            [
                FallbackModel(model="sap/a", params={"temperature": 0.1}),
                FallbackModel(model="sap/b", params={"max_tokens": 100}),
            ]
        )
        out = cfg.to_litellm_kwarg()
        assert out[0] == {"model": "sap/a", "temperature": 0.1}
        assert out[1] == {"model": "sap/b", "max_tokens": 100}


# ---------------------------------------------------------------------------
# FallbackConfig.from_env
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_fallback_env(monkeypatch):
    """Clear every AICORE_FALLBACK_* variable before each test."""
    for key in list(os.environ):
        if key.startswith("AICORE_FALLBACK"):
            monkeypatch.delenv(key, raising=False)
    yield


class TestFromEnv:
    def test_returns_none_when_enabled_absent(self):
        assert FallbackConfig.from_env() is None

    def test_returns_none_when_enabled_false(self, monkeypatch):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "false")
        monkeypatch.setenv("AICORE_FALLBACK_MODELS", "sap/x")
        assert FallbackConfig.from_env() is None

    def test_returns_none_when_enabled_true_but_nothing_set(self, monkeypatch, caplog):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "true")
        with caplog.at_level(logging.WARNING):
            assert FallbackConfig.from_env() is None
        assert any("fallback remains inactive" in r.message for r in caplog.records)

    def test_parses_models_csv(self, monkeypatch):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "true")
        monkeypatch.setenv("AICORE_FALLBACK_MODELS", "sap/a, sap/b ,sap/c")
        cfg = FallbackConfig.from_env()
        assert cfg is not None
        assert [m.model for m in cfg.models] == ["sap/a", "sap/b", "sap/c"]
        # No params or version inherited from env in the simple form.
        assert all(m.params is None and m.model_version is None for m in cfg.models)

    def test_parses_models_csv_skips_empty_entries(self, monkeypatch):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "true")
        monkeypatch.setenv("AICORE_FALLBACK_MODELS", ",sap/a,,sap/b,")
        cfg = FallbackConfig.from_env()
        assert cfg is not None
        assert [m.model for m in cfg.models] == ["sap/a", "sap/b"]

    def test_parses_config_json(self, monkeypatch):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "true")
        monkeypatch.setenv(
            "AICORE_FALLBACK_CONFIG",
            '[{"model":"sap/a","params":{"temperature":0.7}},'
            ' {"model":"sap/b","model_version":"v2"}]',
        )
        cfg = FallbackConfig.from_env()
        assert cfg is not None
        assert cfg.models[0].model == "sap/a"
        assert cfg.models[0].params == {"temperature": 0.7}
        assert cfg.models[1].model == "sap/b"
        assert cfg.models[1].model_version == "v2"

    def test_config_takes_precedence_over_models(self, monkeypatch):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "true")
        monkeypatch.setenv("AICORE_FALLBACK_MODELS", "sap/from-models")
        monkeypatch.setenv("AICORE_FALLBACK_CONFIG", '[{"model":"sap/from-config"}]')
        cfg = FallbackConfig.from_env()
        assert cfg is not None
        assert [m.model for m in cfg.models] == ["sap/from-config"]

    def test_malformed_json_raises(self, monkeypatch):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "true")
        monkeypatch.setenv("AICORE_FALLBACK_CONFIG", "{not json")
        with pytest.raises(ValueError, match="valid JSON"):
            FallbackConfig.from_env()

    def test_non_list_json_raises(self, monkeypatch):
        monkeypatch.setenv("AICORE_FALLBACK_ENABLED", "true")
        monkeypatch.setenv("AICORE_FALLBACK_CONFIG", '{"model": "sap/x"}')
        with pytest.raises(ValueError, match="decode to a list"):
            FallbackConfig.from_env()
