"""Unit tests for OrchestrationPatchConfig — the fallback-side concerns.

Filtering-side coverage lives in :mod:`tests.aicore.filtering.unit.test_patch`.
This file targets:

- ``transform_request`` injects ``fallback_sap_modules`` into ``optional_params``
  before delegating to super.
- Filtering broadcasts to every module entry when both filtering and fallback
  are active (the behaviour change vs. the original modules[0]-only logic).
- ``transform_response`` attaches ``intermediate_failures`` on the returned
  ``ModelResponse`` (and only when present).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from sap_cloud_sdk.aicore.fallback.fallback import FallbackConfig, FallbackModel
from sap_cloud_sdk.aicore.filtering.exceptions import ContentFilteredError
from sap_cloud_sdk.aicore.filtering.filters import (
    AzureContentFilter,
    ContentFiltering,
    InputFiltering,
    OrchestrationPatchConfig,
    OutputFiltering,
    _install_fallback,
    _install_filter,
)


@pytest.fixture(autouse=True)
def restore_litellm_config():
    """Each test starts with a clean patch state and ends the same way."""
    _install_filter(None)
    _install_fallback(None)
    yield
    _install_filter(None)
    _install_fallback(None)


def _stub_response(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, json=body)


def _default_filtering() -> ContentFiltering:
    return ContentFiltering(
        input_filtering=InputFiltering(filters=[AzureContentFilter()]),
        output_filtering=OutputFiltering(filters=[AzureContentFilter()]),
    )


# ---------------------------------------------------------------------------
# transform_request — fallback injection
# ---------------------------------------------------------------------------


class TestTransformRequestFallback:
    @staticmethod
    def _list_modules_body() -> dict:
        """Body shape litellm produces when fallback is active."""
        return {
            "config": {
                "modules": [
                    {
                        "prompt_templating": {
                            "prompt": {"template": []},
                            "model": {
                                "name": "anthropic--claude-4.5-sonnet",
                                "params": {},
                                "version": "latest",
                            },
                        }
                    },
                    {
                        "prompt_templating": {
                            "prompt": {"template": []},
                            "model": {
                                "name": "mistral-small",
                                "params": {},
                                "version": "latest",
                            },
                        }
                    },
                ]
            }
        }

    @staticmethod
    def _dict_modules_body() -> dict:
        """Body shape litellm produces with no fallback."""
        return {
            "config": {
                "modules": {
                    "prompt_templating": {
                        "prompt": {"template": []},
                        "model": {
                            "name": "anthropic--claude-4.5-sonnet",
                            "params": {},
                            "version": "latest",
                        },
                    }
                }
            }
        }

    @staticmethod
    def _realistic_list_modules_body() -> dict:
        """Body shape litellm actually produces — primary has a real template,
        fallback entries have ``template: []`` because litellm only converts
        the top-level ``messages`` for the primary module. The SDK is
        responsible for broadcasting the primary's template to every
        fallback entry; without that the orchestration server rejects with
        ``config.modules[N].prompt_templating.prompt.template should be
        non-empty`` (the exact failure that reached integration tests).
        """
        primary_template = [{"role": "user", "content": "Reply with 'ok'."}]
        return {
            "config": {
                "modules": [
                    {
                        "prompt_templating": {
                            "prompt": {"template": primary_template},
                            "model": {
                                "name": "anthropic--claude-4.5-sonnet",
                                "params": {},
                                "version": "latest",
                            },
                        }
                    },
                    {
                        "prompt_templating": {
                            "prompt": {"template": []},
                            "model": {
                                "name": "mistral-small",
                                "params": {},
                                "version": "latest",
                            },
                        }
                    },
                ]
            }
        }

    def test_fallback_injected_into_optional_params_before_super(self):
        _install_fallback(FallbackConfig([FallbackModel(model="sap/mistral-small")]))
        optional_params: dict = {}
        captured: dict = {}

        def fake_super_transform(**kwargs):
            captured.update(kwargs)
            return self._list_modules_body()

        with patch(
            "sap_cloud_sdk.aicore.filtering.filters."
            "GenAIHubOrchestrationConfig.transform_request",
            side_effect=fake_super_transform,
        ):
            OrchestrationPatchConfig().transform_request(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[],
                optional_params=optional_params,
                litellm_params={},
                headers={},
            )

        assert captured["optional_params"]["fallback_sap_modules"] == [
            {"model": "sap/mistral-small"}
        ]

    def test_no_fallback_injection_when_inactive(self):
        # Filtering inactive too — but inactive _is_ the default; this test
        # asserts the injection is opt-in.
        optional_params: dict = {}
        with patch(
            "sap_cloud_sdk.aicore.filtering.filters."
            "GenAIHubOrchestrationConfig.transform_request",
            return_value=self._dict_modules_body(),
        ):
            OrchestrationPatchConfig().transform_request(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[],
                optional_params=optional_params,
                litellm_params={},
                headers={},
            )
        assert "fallback_sap_modules" not in optional_params

    def test_filtering_broadcasts_to_every_module_entry(self):
        _install_filter(_default_filtering())
        _install_fallback(FallbackConfig([FallbackModel(model="sap/mistral-small")]))

        with patch(
            "sap_cloud_sdk.aicore.filtering.filters."
            "GenAIHubOrchestrationConfig.transform_request",
            return_value=self._list_modules_body(),
        ):
            body = OrchestrationPatchConfig().transform_request(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[],
                optional_params={},
                litellm_params={},
                headers={},
            )

        modules = body["config"]["modules"]
        assert isinstance(modules, list)
        assert len(modules) == 2
        # Every entry — primary AND fallback — carries filtering.
        for entry in modules:
            assert "filtering" in entry
            assert "input" in entry["filtering"]
            assert "output" in entry["filtering"]

    def test_filtering_on_dict_modules_unchanged_when_no_fallback(self):
        _install_filter(_default_filtering())

        with patch(
            "sap_cloud_sdk.aicore.filtering.filters."
            "GenAIHubOrchestrationConfig.transform_request",
            return_value=self._dict_modules_body(),
        ):
            body = OrchestrationPatchConfig().transform_request(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[],
                optional_params={},
                litellm_params={},
                headers={},
            )

        modules = body["config"]["modules"]
        assert isinstance(modules, dict)
        assert "filtering" in modules

    def test_fallback_only_no_filtering_keys(self):
        _install_fallback(FallbackConfig([FallbackModel(model="sap/mistral-small")]))

        with patch(
            "sap_cloud_sdk.aicore.filtering.filters."
            "GenAIHubOrchestrationConfig.transform_request",
            return_value=self._list_modules_body(),
        ):
            body = OrchestrationPatchConfig().transform_request(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[],
                optional_params={},
                litellm_params={},
                headers={},
            )

        # No filtering installed, so no entry should carry one.
        for entry in body["config"]["modules"]:
            assert "filtering" not in entry

    def test_primary_template_broadcasts_to_fallback_entries(self):
        # Regression: previously fallback entries went out with
        # ``prompt.template == []`` and the orchestration server rejected with
        # ``config.modules[1].prompt_templating.prompt.template should be
        # non-empty``. The patch now copies the primary's template across.
        _install_fallback(FallbackConfig([FallbackModel(model="sap/mistral-small")]))

        with patch(
            "sap_cloud_sdk.aicore.filtering.filters."
            "GenAIHubOrchestrationConfig.transform_request",
            return_value=self._realistic_list_modules_body(),
        ):
            body = OrchestrationPatchConfig().transform_request(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[{"role": "user", "content": "Reply with 'ok'."}],
                optional_params={},
                litellm_params={},
                headers={},
            )

        modules = body["config"]["modules"]
        primary_template = modules[0]["prompt_templating"]["prompt"]["template"]
        assert primary_template, "primary template should be non-empty"
        for entry in modules[1:]:
            assert entry["prompt_templating"]["prompt"]["template"] == primary_template

    def test_template_broadcast_noop_for_single_module_body(self):
        # No fallback installed → litellm emits a single dict (not a list);
        # the broadcast must not touch it. (Also: nothing to broadcast to.)
        with patch(
            "sap_cloud_sdk.aicore.filtering.filters."
            "GenAIHubOrchestrationConfig.transform_request",
            return_value=self._dict_modules_body(),
        ):
            body = OrchestrationPatchConfig().transform_request(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[],
                optional_params={},
                litellm_params={},
                headers={},
            )

        modules = body["config"]["modules"]
        assert isinstance(modules, dict)
        # Untouched — same empty template the fixture started with.
        assert modules["prompt_templating"]["prompt"]["template"] == []

    def test_template_broadcast_skipped_when_primary_template_empty(self):
        # Defensive: if the primary itself somehow has no template, do not
        # propagate the empty value (no point) — leave fallback entries alone.
        _install_fallback(FallbackConfig([FallbackModel(model="sap/mistral-small")]))

        with patch(
            "sap_cloud_sdk.aicore.filtering.filters."
            "GenAIHubOrchestrationConfig.transform_request",
            return_value=self._list_modules_body(),
        ):
            body = OrchestrationPatchConfig().transform_request(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[],
                optional_params={},
                litellm_params={},
                headers={},
            )

        modules = body["config"]["modules"]
        for entry in modules:
            assert entry["prompt_templating"]["prompt"]["template"] == []


# ---------------------------------------------------------------------------
# transform_response — intermediate_failures attachment
# ---------------------------------------------------------------------------


_SUCCESS_BODY_WITH_FAILURES = {
    "request_id": "req-fallback",
    "intermediate_results": {},
    "final_result": {
        "id": "x",
        "object": "chat.completion",
        "model": "mistralai--mistral-small-instruct",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Servus!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"completion_tokens": 5, "prompt_tokens": 10, "total_tokens": 15},
    },
    "intermediate_failures": [
        {
            "code": 400,
            "message": "Model gpt-4o not supported.",
            "location": "Request Body",
        }
    ],
}

_SUCCESS_BODY_NO_FAILURES = {
    "request_id": "req-primary",
    "intermediate_results": {},
    "final_result": {
        "id": "x",
        "object": "chat.completion",
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hi!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"completion_tokens": 5, "prompt_tokens": 10, "total_tokens": 15},
    },
}

_OUTPUT_FILTER_BODY = {
    "request_id": "req-blocked",
    "intermediate_results": {
        "output_filtering": {
            "data": {"choices": [{"index": 0, "azure_content_safety": {"Sexual": 4}}]}
        }
    },
    "final_result": {
        "id": "x",
        "model": "m",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": ""},
                "finish_reason": "content_filter",
            }
        ],
        "usage": {"completion_tokens": 0, "prompt_tokens": 10, "total_tokens": 10},
    },
}


class TestTransformResponseIntermediateFailures:
    def _call(self, response: httpx.Response):
        from litellm.types.utils import ModelResponse

        with patch(
            "sap_cloud_sdk.aicore.filtering.filters."
            "GenAIHubOrchestrationConfig.transform_response",
            return_value=ModelResponse(),
        ):
            return OrchestrationPatchConfig().transform_response(
                model="sap/anthropic--claude-4.5-sonnet",
                raw_response=response,
                model_response=ModelResponse(),
                logging_obj=MagicMock(),
                request_data={},
                messages=[],
                optional_params={},
                litellm_params={},
                encoding=None,
            )

    def test_intermediate_failures_attached_when_present(self):
        result = self._call(_stub_response(200, _SUCCESS_BODY_WITH_FAILURES))
        failures = getattr(result, "intermediate_failures", None)
        assert failures is not None
        assert len(failures) == 1
        assert failures[0]["code"] == 400
        assert "gpt-4o" in failures[0]["message"]

    def test_intermediate_failures_absent_when_key_missing(self):
        result = self._call(_stub_response(200, _SUCCESS_BODY_NO_FAILURES))
        assert getattr(result, "intermediate_failures", None) is None

    def test_output_filter_still_raises_with_intermediate_failures(self):
        # Even if the body carries intermediate_failures, output-filter rejection
        # must take precedence — the response is still a filter block.
        body: dict[str, Any] = dict(_OUTPUT_FILTER_BODY)
        body["intermediate_failures"] = [
            {"code": 429, "message": "rate limited", "location": "LLM"}
        ]
        with pytest.raises(ContentFilteredError) as ei:
            self._call(_stub_response(200, body))
        assert ei.value.direction == "output"


# ---------------------------------------------------------------------------
# Cross-concern install lifecycle (filtering + fallback in one patch)
# ---------------------------------------------------------------------------


class TestInstallComposition:
    def test_patch_installed_when_only_filtering(self):
        import litellm

        from sap_cloud_sdk.aicore.filtering.filters import _ORIGINAL_CONFIG

        _install_filter(_default_filtering())
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig
        _install_filter(None)
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_patch_installed_when_only_fallback(self):
        import litellm

        from sap_cloud_sdk.aicore.filtering.filters import _ORIGINAL_CONFIG

        _install_fallback(FallbackConfig([FallbackModel(model="sap/x")]))
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig
        _install_fallback(None)
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_patch_stays_when_one_concern_cleared_other_active(self):
        import litellm

        _install_filter(_default_filtering())
        _install_fallback(FallbackConfig([FallbackModel(model="sap/x")]))
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig

        # Clear only filtering — patch stays because fallback is still active.
        _install_filter(None)
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig

        # Clear fallback — now both inactive, original restored.
        _install_fallback(None)
        from sap_cloud_sdk.aicore.filtering.filters import _ORIGINAL_CONFIG

        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_install_fallback_idempotent(self):
        import litellm

        cfg = FallbackConfig([FallbackModel(model="sap/x")])
        _install_fallback(cfg)
        _install_fallback(cfg)
        assert litellm.GenAIHubOrchestrationConfig is OrchestrationPatchConfig
