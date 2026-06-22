"""Unit tests for aicore.filtering._litellm_patch."""

import json
import pytest
from unittest.mock import MagicMock, patch

import httpx

from sap_cloud_sdk.aicore.filtering._filters import AzureContentFilter
from sap_cloud_sdk.aicore.filtering._modules import (
    ContentFiltering,
    InputFiltering,
    OutputFiltering,
)
from sap_cloud_sdk.aicore.filtering._litellm_patch import (
    FilteringOrchestrationConfig,
    _install,
    _ORIGINAL_CONFIG,
    extract_filter_blocked,
)
from sap_cloud_sdk.aicore.filtering.exceptions import ContentFilteredError


@pytest.fixture(autouse=True)
def restore_litellm_config():
    yield
    _install(None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_response(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, json=body)


INPUT_FILTER_BODY = {
    "error": {
        "request_id": "req-abc",
        "code": 400,
        "message": "Content filtered.",
        "location": "Filtering Module - Input Filter",
        "intermediate_results": {
            "templating": [{"content": "bad prompt", "role": "user"}],
            "input_filtering": {
                "data": {
                    "azure_content_safety": {
                        "Hate": 0,
                        "Violence": 4,
                        "SelfHarm": 0,
                        "Sexual": 0,
                    }
                }
            },
        },
    }
}

OUTPUT_FILTER_BODY = {
    "request_id": "req-xyz",
    "intermediate_results": {
        "output_filtering": {
            "data": {"choices": [{"index": 0, "azure_content_safety": {"Sexual": 2}}]}
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

SUCCESS_BODY = {
    "request_id": "req-ok",
    "intermediate_results": {},
    "final_result": {
        "id": "x",
        "object": "chat.completion",
        "model": "claude-sonnet-4-5",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"completion_tokens": 5, "prompt_tokens": 10, "total_tokens": 15},
    },
}


# ---------------------------------------------------------------------------
# transform_request tests
# ---------------------------------------------------------------------------


class TestTransformRequest:
    @staticmethod
    def _fresh_base_body() -> dict:
        return {
            "config": {
                "modules": {
                    "prompt_templating": {
                        "prompt": {"template": [{"role": "user", "content": "hello"}]},
                        "model": {
                            "name": "anthropic--claude-4.5-sonnet",
                            "params": {},
                            "version": "latest",
                        },
                    }
                }
            }
        }

    def _call(self, filtering):
        _install(filtering)
        with patch(
            "sap_cloud_sdk.aicore.filtering._litellm_patch.GenAIHubOrchestrationConfig.transform_request",
            return_value=self._fresh_base_body(),
        ):
            return FilteringOrchestrationConfig().transform_request(
                model="sap/anthropic--claude-4.5-sonnet",
                messages=[{"role": "user", "content": "hello"}],
                optional_params={},
                litellm_params={},
                headers={},
            )

    def test_filtering_injected_when_active(self, monkeypatch):
        for k in list(__import__("os").environ):
            if k.startswith("AICORE_FILTER"):
                monkeypatch.delenv(k, raising=False)
        body = self._call(ContentFiltering.from_env())
        assert "filtering" in body["config"]["modules"]

    def test_both_directions_present_by_default(self, monkeypatch):
        for k in list(__import__("os").environ):
            if k.startswith("AICORE_FILTER"):
                monkeypatch.delenv(k, raising=False)
        body = self._call(ContentFiltering.from_env())
        filtering = body["config"]["modules"]["filtering"]
        assert "input" in filtering
        assert "output" in filtering

    def test_no_filtering_when_cfg_none(self):
        body = self._call(None)
        assert "filtering" not in body["config"]["modules"]

    def test_prompt_shield_on_input(self, monkeypatch):
        for k in list(__import__("os").environ):
            if k.startswith("AICORE_FILTER"):
                monkeypatch.delenv(k, raising=False)
        body = self._call(ContentFiltering.from_env())
        in_cfg = body["config"]["modules"]["filtering"]["input"]["filters"][0]["config"]
        assert in_cfg.get("prompt_shield") is True


# ---------------------------------------------------------------------------
# transform_response tests
# ---------------------------------------------------------------------------


class TestTransformResponse:
    def _call_transform_response(self, response: httpx.Response):
        from litellm.types.utils import ModelResponse

        with patch(
            "sap_cloud_sdk.aicore.filtering._litellm_patch.GenAIHubOrchestrationConfig.transform_response",
            return_value=ModelResponse(),
        ):
            return FilteringOrchestrationConfig().transform_response(
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

    def test_input_filter_4xx_raises(self):
        with pytest.raises(ContentFilteredError) as ei:
            self._call_transform_response(_stub_response(400, INPUT_FILTER_BODY))
        assert ei.value.direction == "input"
        assert ei.value.request_id == "req-abc"
        # prompt text must NOT be in details
        assert "bad prompt" not in str(ei.value.details)
        assert "templating" not in ei.value.details

    def test_output_filter_200_raises(self):
        with pytest.raises(ContentFilteredError) as ei:
            self._call_transform_response(_stub_response(200, OUTPUT_FILTER_BODY))
        assert ei.value.direction == "output"
        assert ei.value.request_id == "req-xyz"

    def test_success_delegates_to_super(self):
        result = self._call_transform_response(_stub_response(200, SUCCESS_BODY))
        assert result is not None

    def test_non_filter_4xx_delegates_to_super(self):
        body = {
            "error": {"code": 422, "message": "bad model", "location": "Model Module"}
        }
        result = self._call_transform_response(_stub_response(422, body))
        assert result is not None  # no ContentFilteredError raised


# ---------------------------------------------------------------------------
# extract_filter_blocked tests
# ---------------------------------------------------------------------------


class TestExtractFilterBlocked:
    def _make_exc(self, payload: dict) -> Exception:
        return Exception(f"SapException - {json.dumps(payload)}")

    def test_extracts_input_filter(self):
        exc = self._make_exc(INPUT_FILTER_BODY)
        blocked = extract_filter_blocked(exc)
        assert blocked is not None
        assert blocked.direction == "input"
        assert blocked.request_id == "req-abc"
        assert blocked.details.get("azure_content_safety", {}).get("Violence") == 4

    def test_returns_none_for_non_filter_exception(self):
        assert extract_filter_blocked(Exception("network error")) is None

    def test_returns_none_for_other_location(self):
        body = {"error": {"location": "Model Module", "message": "model not found"}}
        exc = self._make_exc(body)
        assert extract_filter_blocked(exc) is None

    def test_returns_none_for_malformed_json(self):
        assert extract_filter_blocked(Exception("{ not valid json }")) is None


# ---------------------------------------------------------------------------
# _install tests
# ---------------------------------------------------------------------------


class TestInstall:
    def _default_cfg(self) -> ContentFiltering:
        return ContentFiltering(
            input_filtering=InputFiltering(filters=[AzureContentFilter()]),
            output_filtering=OutputFiltering(filters=[AzureContentFilter()]),
        )

    def test_install_patches_litellm(self):
        import litellm

        cfg = self._default_cfg()
        _install(cfg)
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig
        _install(None)  # restore

    def test_install_none_restores_original(self):
        import litellm

        _install(self._default_cfg())
        _install(None)
        assert litellm.GenAIHubOrchestrationConfig is _ORIGINAL_CONFIG

    def test_install_idempotent(self):
        import litellm

        cfg = self._default_cfg()
        _install(cfg)
        _install(cfg)  # second call — no error
        assert litellm.GenAIHubOrchestrationConfig is FilteringOrchestrationConfig
        _install(None)
