"""LiteLLM provider patch that injects content filtering into SAP Orchestration v2 calls.

Patches ``litellm.GenAIHubOrchestrationConfig`` with a subclass that:
- Injects ``modules.filtering`` into every v2 completion request body
- Detects filter rejections in responses and raises ``ContentFilteredError``

The patch is applied by ``_install(cfg)`` and undone by ``_install(None)``.
It is idempotent — calling it multiple times with the same config is safe.

Two filter rejection shapes (from the v2 API) are handled:
- Input rejection: HTTP 4xx, ``error.location`` startswith
  ``"Filtering Module - Input Filter"`` (content-filtering.md L130-162)
- Output rejection: HTTP 200, ``finish_reason == "content_filter"``,
  empty ``message.content`` (content-filtering.md L234-303)

LiteLLM's ``raise_for_status()`` turns 4xx responses into
``httpx.HTTPStatusError`` before ``transform_response`` is reached,
so input-filter 400s arrive wrapped in a ``litellm.APIConnectionError``
with the JSON embedded in the exception message.
``extract_filter_blocked()`` handles that case.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import litellm
from litellm.llms.sap.chat.transformation import GenAIHubOrchestrationConfig
from litellm.types.utils import ModelResponse

from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation

from .exceptions import ContentFilteredError

logger = logging.getLogger(__name__)

# Keep the original so _install(None) can restore it.
_ORIGINAL_CONFIG = litellm.GenAIHubOrchestrationConfig

_active_cfg: Any = None  # FilteringModuleConfig | None, stored at module level


class FilteringOrchestrationConfig(GenAIHubOrchestrationConfig):
    """GenAIHubOrchestrationConfig subclass that injects content filtering."""

    def transform_request(
        self,
        model: str,
        messages: list,
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        body = super().transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        if _active_cfg is None:
            return body

        filtering_dict = _active_cfg.to_dict()
        if not filtering_dict:
            return body

        modules = body["config"]["modules"]
        if isinstance(modules, list):
            # Fallback mode (list of configs) — inject into primary config only.
            modules[0]["filtering"] = filtering_dict
        else:
            modules["filtering"] = filtering_dict

        return body

    def transform_response(
        self,
        model: str,
        raw_response: Any,
        model_response: ModelResponse,
        logging_obj: Any,
        request_data: dict,
        messages: list,
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: str | None = None,
        json_mode: bool | None = None,
    ) -> ModelResponse:
        status = raw_response.status_code

        # Input-filter rejection (HTTP 4xx).
        # content-filtering.md L130-162: error.location identifies the filter module.
        if 400 <= status < 500:
            try:
                err = raw_response.json().get("error", {})
                if (err.get("location") or "").startswith(
                    "Filtering Module - Input Filter"
                ):
                    data = (
                        err.get("intermediate_results", {})
                        .get("input_filtering", {})
                        .get("data", {})
                    )
                    raise ContentFilteredError(
                        direction="input",
                        details=data,
                        request_id=err.get("request_id"),
                    )
            except ContentFilteredError:
                raise
            except Exception:
                pass

        # Output-filter rejection (HTTP 200 + finish_reason == "content_filter").
        # content-filtering.md L234-303: message.content is "" (empty, not absent).
        if status == 200:
            try:
                payload = raw_response.json()
                choices = (payload.get("final_result") or {}).get("choices") or []
                if choices and choices[0].get("finish_reason") == "content_filter":
                    data = (
                        payload.get("intermediate_results", {})
                        .get("output_filtering", {})
                        .get("data", {})
                    )
                    raise ContentFilteredError(
                        direction="output",
                        details=data,
                        request_id=payload.get("request_id"),
                    )
            except ContentFilteredError:
                raise
            except Exception:
                pass

        return super().transform_response(
            model=model,
            raw_response=raw_response,
            model_response=model_response,
            logging_obj=logging_obj,
            request_data=request_data,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            encoding=encoding,
            api_key=api_key,
            json_mode=json_mode,
        )


def _install(cfg: Any) -> None:  # cfg: FilteringModuleConfig | None
    """Patch litellm.GenAIHubOrchestrationConfig. Idempotent.

    cfg=None restores the original config and disables filtering.
    """
    global _active_cfg
    _active_cfg = cfg
    if cfg is None:
        litellm.GenAIHubOrchestrationConfig = _ORIGINAL_CONFIG  # type: ignore[attr-defined]
        logger.debug("orchestration filtering disabled")
    else:
        litellm.GenAIHubOrchestrationConfig = FilteringOrchestrationConfig  # type: ignore[attr-defined]
        logger.info("orchestration filtering active (FilteringOrchestrationConfig)")


@record_metrics(Module.AICORE, Operation.AICORE_EXTRACT_FILTER_BLOCKED)
def extract_filter_blocked(exc: Exception) -> ContentFilteredError | None:
    """Parse a LiteLLM APIConnectionError for an input-filter rejection.

    When Azure Content Safety blocks the input, LiteLLM's ``raise_for_status()``
    converts the 400 into an ``httpx.HTTPStatusError``, which is then wrapped
    into a ``litellm.APIConnectionError`` with the original JSON embedded in
    the exception message string. This function extracts it.

    Returns None if the exception is not a content-filter rejection.

    A telemetry event is emitted on every call, including calls where the
    exception was not a content-filter rejection (returns ``None``).
    """
    msg = str(exc)
    brace = msg.find("{")
    if brace == -1:
        return None
    try:
        payload = json.loads(msg[brace:])
        err = payload.get("error", {})
        if not (err.get("location") or "").startswith(
            "Filtering Module - Input Filter"
        ):
            return None
        data = (
            err.get("intermediate_results", {})
            .get("input_filtering", {})
            .get("data", {})
        )
        return ContentFilteredError(
            direction="input",
            details=data,
            request_id=err.get("request_id"),
        )
    except Exception:
        return None
