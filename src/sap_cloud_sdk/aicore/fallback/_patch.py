"""LiteLLM transport patch that adds model-fallback support on top of filtering.

Patches ``litellm.GenAIHubOrchestrationConfig`` with a subclass of the
filtering patch (:class:`sap_cloud_sdk.aicore.filtering._patch.FilteringOrchestrationConfig`)
that adds the fallback-side hooks:

- ``transform_request``:
  1. Injects ``fallback_sap_modules`` into ``optional_params`` before super
     reads it. LiteLLM's ``GenAIHubOrchestrationConfig.transform_request``
     pops that key to build ``body["config"]["modules"]`` as a list.
  2. After super returns, copies the primary module's prompt template into
     every fallback module entry — litellm builds the primary template from
     ``messages`` but defaults each fallback's template to ``[]``, which the
     orchestration server rejects with
     ``"config.modules[N].prompt_templating.prompt.template should be non-empty"``.
  3. When filtering is active, broadcasts the filtering configuration across
     every module entry (primary + every fallback). The filtering parent
     class only injects on ``modules[0]``; the broadcast here keeps the
     same filter set applied for every preference the server might pick.

- ``transform_response``: after super has handled filter-rejection detection,
  attaches ``intermediate_failures`` (the per-preference failure list) from
  the 200 response body onto the returned :class:`ModelResponse` so callers
  can inspect which preferences were skipped. ``None`` when the primary
  succeeded. Non-streaming only in v1.

The two patches share the monkeypatch slot. :func:`_install_fallback`
installs this subclass (which still does filtering thanks to inheritance);
clearing fallback restores the filtering-only class (or the original) by
calling :func:`sap_cloud_sdk.aicore.filtering._patch._install` with the
filtering side's current state — that path knows nothing about fallback,
so the filtering module never imports this one. Idempotent.
"""

from __future__ import annotations

import logging
from typing import Any

import litellm
from litellm.types.utils import ModelResponse

from ..filtering import _patch as _filter_patch
from ..filtering._patch import FilteringOrchestrationConfig

logger = logging.getLogger(__name__)


# Module-level fallback state. ``None`` means fallback is inactive; the
# filtering module is the source of truth for the installed class in that
# case (see :func:`_install_fallback`).
_active_fallback_cfg: Any = None  # FallbackConfig | None


class OrchestrationPatchConfig(FilteringOrchestrationConfig):
    """Adds model-fallback request/response hooks to the filtering patch.

    Inherits filtering injection + rejection handling from
    :class:`FilteringOrchestrationConfig`. Adds, in order:

    - ``fallback_sap_modules`` injection (so litellm builds ``modules`` as a
      list of preference dicts).
    - Prompt-template broadcast to every fallback module entry.
    - Filtering broadcast across every module entry (overriding the parent's
      primary-only injection).
    - ``intermediate_failures`` attachment on the returned ``ModelResponse``.
    """

    def transform_request(
        self,
        model: str,
        messages: list,
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        # Inject fallback into optional_params BEFORE super reads it.
        # LiteLLM's transform_request copies optional_params and pops
        # ``"fallback_sap_modules"`` to build the modules list.
        if _active_fallback_cfg is not None:
            optional_params["fallback_sap_modules"] = (
                _active_fallback_cfg.to_litellm_kwarg()
            )

        body = super().transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        modules = body["config"]["modules"]
        # No fallback => single dict, nothing else to do here.
        if not isinstance(modules, list) or len(modules) <= 1:
            return body

        # Broadcast the primary's prompt template to every fallback entry.
        # litellm only builds the primary's template from ``messages``;
        # fallback entries get whatever was popped from their dict's
        # ``"messages"`` key (litellm transformation.py L371), which is
        # ``[]`` for ``FallbackModel.to_dict()``. Without this copy, the
        # server rejects with
        # "config.modules[N].prompt_templating.prompt.template should be
        # non-empty".
        primary_template = (
            modules[0].get("prompt_templating", {}).get("prompt", {}).get("template")
        )
        if primary_template:
            for entry in modules[1:]:
                entry.setdefault("prompt_templating", {}).setdefault("prompt", {})[
                    "template"
                ] = primary_template

        # Broadcast filtering across every module entry. The filtering parent
        # installed it on ``modules[0]`` only; broadcasting keeps the same
        # filter set applied for every preference the server might pick.
        # To opt a fallback out of filtering, call ``disable_filtering()``
        # before the call.
        if _filter_patch._active_cfg is not None:
            filtering_dict = _filter_patch._active_cfg.to_dict()
            if filtering_dict:
                for entry in modules[1:]:
                    entry["filtering"] = filtering_dict

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
        # Let the filtering parent handle filter-rejection detection first
        # (it raises ``ContentFilteredError`` before falling through to
        # super-super). If it raises, we never reach the attach below.
        result = super().transform_response(
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

        # Surface ``intermediate_failures`` on the returned ``ModelResponse``
        # so callers can see which preferences were skipped. Only present on
        # non-streaming 200 responses — streaming surfacing is deferred.
        if raw_response.status_code == 200:
            try:
                payload = raw_response.json()
            except ValueError:
                return result
            failures = payload.get("intermediate_failures")
            if failures is not None:
                # ``ModelResponse`` uses pydantic ``extra="allow"`` so dynamic
                # attribute assignment is supported at runtime. ``setattr``
                # keeps the static type checker happy.
                setattr(result, "intermediate_failures", failures)

        return result


def _install_fallback(cfg: Any) -> None:  # cfg: FallbackConfig | None
    """Set the active fallback config and refresh the installed patch class.

    When ``cfg`` is non-``None``, installs :class:`OrchestrationPatchConfig`
    (which inherits filtering, so filtering still works when active).

    When ``cfg`` is ``None``, defers to the filtering module: re-runs its
    ``_install`` with whatever filtering state is currently active, which
    restores either ``FilteringOrchestrationConfig`` (filtering on) or
    ``_ORIGINAL_CONFIG`` (both off).

    Idempotent — repeated calls with the same value are safe.
    """
    global _active_fallback_cfg
    _active_fallback_cfg = cfg
    if cfg is None:
        # Hand back control to the filtering installer so it restores the
        # correct class for the current filtering state.
        _filter_patch._install(_filter_patch._active_cfg)
        logger.debug("model fallback disabled")
    else:
        litellm.GenAIHubOrchestrationConfig = OrchestrationPatchConfig
        logger.info("model fallback active (OrchestrationPatchConfig)")
