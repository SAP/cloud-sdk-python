"""LiteLLM transport patch that injects content filtering into v2 calls.

Patches ``litellm.GenAIHubOrchestrationConfig`` with a subclass that:

- Injects ``modules.filtering`` into every v2 completion request body via
  ``transform_request``.
- Detects filter rejections in buffered responses and raises
  ``ContentFilteredError`` via ``transform_response``.

The patch is applied by :func:`_install` (called by ``set_filtering`` /
``disable_filtering`` in :mod:`.filters`) and is idempotent — calling it
multiple times with the same config is safe.

Two filter-rejection shapes (from the v2 API) are handled in buffered mode:

- Input rejection: HTTP 4xx with ``error.location`` startswith
  ``"Filtering Module - Input Filter"``.
- Output rejection: HTTP 200 with ``finish_reason == "content_filter"`` and
  empty ``message.content``.

LiteLLM's ``raise_for_status()`` turns 4xx responses into
``httpx.HTTPStatusError`` before ``transform_response`` is reached, so
input-filter 400s arrive wrapped in a ``litellm.APIConnectionError`` with
the JSON embedded in the exception message.
:func:`sap_cloud_sdk.aicore.completion` translates the wrapped exception
back into :class:`ContentFilteredError` before it reaches caller code; the
:func:`_parse_input_filter_error` helper in :mod:`.filters` does the JSON
parsing.

Streaming + output filtering
----------------------------
The SAP AI Core Orchestration v2 API supports output filtering with streaming.
The server filters each chunk and signals a rejection via an in-stream error
event (no ``[DONE]``). LiteLLM's ``SAPStreamIterator`` surfaces this error
event as a ``ValueError(json.dumps(event_obj))`` from inside the iterator.

:func:`sap_cloud_sdk.aicore.completion` / :func:`acompletion` wrap the
returned stream iterator when output filtering is active, catching that
``ValueError`` and translating it to :class:`ContentFilteredError`. This gives
callers a single, typed exception for filter rejections in both streaming and
non-streaming modes.

Note: agent frameworks (``ChatLiteLLM``, LangGraph, etc.) that call
``litellm.completion`` directly — bypassing the SDK's completion wrapper —
will see the raw ``ValueError`` from the iterator. They must either use
:func:`sap_cloud_sdk.aicore.completion` to get the translated error, or
handle the ``ValueError`` themselves.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import litellm
from litellm.llms.sap.chat.transformation import GenAIHubOrchestrationConfig
from litellm.types.utils import ModelResponse

from .exceptions import ContentFilteredError

logger = logging.getLogger(__name__)

# Keep the original so _install(None) can restore it.
_ORIGINAL_CONFIG = litellm.GenAIHubOrchestrationConfig

_active_cfg: Any = None  # ContentFiltering | None, stored at module level


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
            for m in modules:
                m["filtering"] = filtering_dict
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
        if 400 <= status < 500:
            try:
                body = raw_response.json()
            except ValueError:
                # Response wasn't JSON (gateway error page, plain-text 5xx,
                # truncated body, etc.) — not a filter rejection, fall through
                # to LiteLLM's default handling.
                body = None
            if body is not None:
                err = body.get("error", {})
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

        # Output-filter rejection (HTTP 200 + finish_reason == "content_filter").
        if status == 200:
            try:
                payload = raw_response.json()
            except ValueError:
                # Response wasn't JSON — pass through to LiteLLM.
                payload = None
            if payload is not None:
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


def _install(cfg: Any) -> None:  # cfg: ContentFiltering | None
    """Patch litellm.GenAIHubOrchestrationConfig. Idempotent.

    cfg=None restores the original config and disables filtering.
    """
    global _active_cfg
    _active_cfg = cfg
    if cfg is None:
        litellm.GenAIHubOrchestrationConfig = _ORIGINAL_CONFIG
        logger.debug("content filtering disabled")
    else:
        litellm.GenAIHubOrchestrationConfig = FilteringOrchestrationConfig
        logger.info("content filtering active (FilteringOrchestrationConfig)")


def _parse_output_filter_stream_error(
    exc: BaseException,
) -> ContentFilteredError | None:
    """Try to parse an in-stream output-filter rejection from a ValueError.

    LiteLLM's ``SAPStreamIterator`` raises ``ValueError(json.dumps(event_obj))``
    when the server sends an error event inside the stream.  The v2 error shape
    for an output-filter rejection is::

        {"error": {"request_id": "...", "code": 500,
                   "message": "...",
                   "location": "Filtering Module - Output Filter",
                   "intermediate_results": {"output_filtering": {"data": {...}}}}}

    Returns a :class:`ContentFilteredError` when the pattern matches, otherwise
    ``None`` so the caller can re-raise the original exception unchanged.
    """
    if not isinstance(exc, (ValueError, Exception)):
        return None
    msg = str(exc)
    brace = msg.find("{")
    if brace == -1:
        return None
    try:
        payload = json.loads(msg[brace:])
    except (ValueError, TypeError):
        return None
    err = payload.get("error", {})
    if not isinstance(err, dict):
        return None
    location = err.get("location") or ""
    if not location.startswith("Filtering Module - Output Filter"):
        return None
    data = (
        err.get("intermediate_results", {}).get("output_filtering", {}).get("data", {})
    )
    return ContentFilteredError(
        direction="output",
        details=data,
        request_id=err.get("request_id"),
    )
