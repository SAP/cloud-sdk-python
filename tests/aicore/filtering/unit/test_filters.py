"""Unit tests for aicore.filtering._filters provider classes."""

import pytest

from sap_cloud_sdk.aicore.filtering._filters import (
    AzureContentFilter,
    ContentFilter,
    LlamaGuard38bFilter,
)
from sap_cloud_sdk.aicore.filtering._models import Severity


class TestContentFilterBase:
    def test_to_dict_emits_provider_and_config(self):
        """Base class emits ``{"type": provider, "config": config}``."""
        f = ContentFilter()
        f.provider = "custom_provider"
        f.config = {"foo": "bar"}
        assert f.to_dict() == {"type": "custom_provider", "config": {"foo": "bar"}}


class TestAzureContentFilter:
    def test_provider_is_azure_content_safety(self):
        f = AzureContentFilter()
        assert f.provider == "azure_content_safety"

    def test_defaults_all_medium(self):
        f = AzureContentFilter()
        assert f.config == {"hate": 4, "violence": 4, "sexual": 4, "self_harm": 4}

    def test_to_dict_default(self):
        assert AzureContentFilter().to_dict() == {
            "type": "azure_content_safety",
            "config": {"hate": 4, "violence": 4, "sexual": 4, "self_harm": 4},
        }

    def test_prompt_shield_true_appends_key(self):
        f = AzureContentFilter(prompt_shield=True)
        assert f.config["prompt_shield"] is True

    def test_prompt_shield_false_omits_key(self):
        f = AzureContentFilter(prompt_shield=False)
        assert "prompt_shield" not in f.config

    def test_prompt_shield_default_omits_key(self):
        """Default is prompt_shield=False so the key must not appear."""
        f = AzureContentFilter()
        assert "prompt_shield" not in f.config

    def test_accepts_severity_enum(self):
        f = AzureContentFilter(
            hate=Severity.STRICT,
            violence=Severity.LOW,
            sexual=Severity.MEDIUM,
            self_harm=Severity.OFF,
        )
        assert f.config == {"hate": 0, "violence": 2, "sexual": 4, "self_harm": 6}

    def test_accepts_raw_int(self):
        f = AzureContentFilter(hate=0, violence=2, sexual=4, self_harm=6)
        assert f.config == {"hate": 0, "violence": 2, "sexual": 4, "self_harm": 6}

    def test_enum_and_int_equivalent(self):
        a = AzureContentFilter(hate=Severity.STRICT)
        b = AzureContentFilter(hate=0)
        assert a.to_dict() == b.to_dict()

    def test_invalid_int_raises(self):
        with pytest.raises(ValueError):
            AzureContentFilter(hate=3)

    def test_kwarg_only(self):
        """Positional construction must fail — all params are keyword-only."""
        with pytest.raises(TypeError):
            AzureContentFilter(0, 0, 0, 0)  # type: ignore[misc]

    def test_config_values_are_plain_int_not_severity(self):
        """The dict values must be ``int`` so JSON serialisation is unambiguous."""
        f = AzureContentFilter(hate=Severity.STRICT)
        assert type(f.config["hate"]) is int


class TestLlamaGuard38bFilter:
    def test_provider_is_llama_guard(self):
        f = LlamaGuard38bFilter()
        assert f.provider == "llama_guard_3_8b"

    def test_defaults_all_false(self):
        f = LlamaGuard38bFilter()
        assert all(v is False for v in f.config.values())

    def test_has_fourteen_categories(self):
        f = LlamaGuard38bFilter()
        assert len(f.config) == 14

    def test_to_dict_default(self):
        d = LlamaGuard38bFilter().to_dict()
        assert d["type"] == "llama_guard_3_8b"
        assert all(v is False for v in d["config"].values())

    def test_each_flag_toggles_independently(self):
        f = LlamaGuard38bFilter(hate=True, self_harm=True)
        assert f.config["hate"] is True
        assert f.config["self_harm"] is True
        # The other 12 stay False
        other_keys = set(f.config) - {"hate", "self_harm"}
        assert all(f.config[k] is False for k in other_keys)

    def test_all_fourteen_categories_present_as_keys(self):
        f = LlamaGuard38bFilter()
        expected = {
            "violent_crimes",
            "non_violent_crimes",
            "sex_crimes",
            "child_exploitation",
            "defamation",
            "specialized_advice",
            "privacy",
            "intellectual_property",
            "indiscriminate_weapons",
            "hate",
            "self_harm",
            "sexual_content",
            "elections",
            "code_interpreter_abuse",
        }
        assert set(f.config) == expected

    def test_kwarg_only(self):
        with pytest.raises(TypeError):
            LlamaGuard38bFilter(True)  # type: ignore[misc]

    def test_inherits_from_content_filter(self):
        assert isinstance(LlamaGuard38bFilter(), ContentFilter)


class TestAzureFilterInheritsContentFilter:
    def test_inheritance(self):
        assert isinstance(AzureContentFilter(), ContentFilter)
