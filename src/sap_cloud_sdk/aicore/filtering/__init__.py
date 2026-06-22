"""SAP AI Core content filtering — Azure Content Safety + Prompt Shield.

Filtering is **enabled by default** when :func:`sap_cloud_sdk.aicore.set_aicore_config`
is called. No additional code is required. To override thresholds, use
:func:`set_filtering`; to turn filtering off at runtime, use
:func:`disable_filtering`; alternatively set ``AICORE_FILTER_*`` environment
variables before :func:`set_aicore_config`.

See :mod:`sap_cloud_sdk.aicore` user guide for the documented public API.
"""

from __future__ import annotations

import logging
from typing import Literal

from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation

from ._litellm_patch import _install, extract_filter_blocked
from ._models import (
    ContentFilterConfig,
    FilteringModuleConfig,
    PromptShieldConfig,
    Severity,
)
from .exceptions import ContentFilteredError, OrchestrationError

logger = logging.getLogger(__name__)

__all__ = [
    "set_filtering",
    "disable_filtering",
    "Severity",
    "ContentFilterConfig",
    "PromptShieldConfig",
    "FilteringModuleConfig",
    "ContentFilteredError",
    "OrchestrationError",
    "extract_filter_blocked",
]


@record_metrics(Module.AICORE, Operation.AICORE_SET_FILTERING)
def set_filtering(
    *,
    hate: Severity | None = None,
    violence: Severity | None = None,
    sexual: Severity | None = None,
    self_harm: Severity | None = None,
    prompt_shield: bool | None = None,
    directions: set[Literal["input", "output"]] | None = None,
) -> None:
    """Override content filtering thresholds programmatically.

    Filtering is already activated by :func:`set_aicore_config` — this
    function is only needed to override specific thresholds at runtime.
    Any argument left as ``None`` retains its current value (from env
    vars or defaults).

    To turn filtering off, call :func:`disable_filtering` instead.

    Args:
        hate: Hate severity threshold.
        violence: Violence severity threshold.
        sexual: Sexual severity threshold.
        self_harm: Self-harm severity threshold.
        prompt_shield: Enable/disable jailbreak + indirect injection
            detection (input-only).
        directions: Set of directions to filter. Default is
            ``{"input", "output"}``.

    Examples:
        Tighten two thresholds::

            set_filtering(self_harm=Severity.STRICT, violence=Severity.STRICT)

        Re-apply env-var config after changing variables::

            set_filtering()
    """
    # No args at all — re-apply env-based config (respects AICORE_FILTER_ENABLED)
    if all(
        v is None
        for v in [hate, violence, sexual, self_harm, prompt_shield, directions]
    ):
        _install(FilteringModuleConfig.from_env())
        return

    # Some args provided — start from env-based config then override.
    # If env says disabled, fall back to a defaults config so the
    # programmatic override wins.
    base = FilteringModuleConfig.from_env() or FilteringModuleConfig()

    def _effective_filter(
        existing: ContentFilterConfig | None,
    ) -> ContentFilterConfig | None:
        if existing is None and directions is not None and "input" not in directions:
            return None
        src = existing or ContentFilterConfig()
        return ContentFilterConfig(
            hate=hate if hate is not None else src.hate,
            violence=violence if violence is not None else src.violence,
            sexual=sexual if sexual is not None else src.sexual,
            self_harm=self_harm if self_harm is not None else src.self_harm,
        )

    new_input = (
        _effective_filter(base.input_filter)
        if (directions is None or "input" in (directions or {"input", "output"}))
        else None
    )
    new_output = (
        _effective_filter(base.output_filter)
        if (directions is None or "output" in (directions or {"input", "output"}))
        else None
    )

    new_shield = base.prompt_shield
    if prompt_shield is not None:
        new_shield = PromptShieldConfig(enabled=prompt_shield)

    cfg = FilteringModuleConfig(
        input_filter=new_input,
        output_filter=new_output,
        prompt_shield=new_shield,
    )
    _install(cfg)


@record_metrics(Module.AICORE, Operation.AICORE_DISABLE_FILTERING)
def disable_filtering() -> None:
    """Disable content filtering for SAP AI Core model calls.

    Restores the original ``litellm.GenAIHubOrchestrationConfig``.
    Idempotent — safe to call when filtering is already disabled.
    """
    _install(None)
