"""SAP AI Core Orchestration — content filtering and prompt shield.

Filtering is **enabled by default** when ``set_aicore_config()`` is called.
No additional code is required. To override thresholds, use ``set_filtering()``
or set ``ORCH_FILTER_*`` environment variables.

See user-guide.md for full documentation.
"""

from __future__ import annotations

import logging
from typing import Literal

from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation

from ._litellm_patch import _install, extract_filter_blocked
from ._models import ContentFilterConfig, FilteringModuleConfig, PromptShieldConfig
from .exceptions import ContentFilteredError, OrchestrationError

logger = logging.getLogger(__name__)

__all__ = [
    "set_filtering",
    "ContentFilterConfig",
    "PromptShieldConfig",
    "FilteringModuleConfig",
    "ContentFilteredError",
    "OrchestrationError",
    "extract_filter_blocked",
]


@record_metrics(Module.ORCHESTRATION, Operation.ORCHESTRATION_SET_FILTERING)
def set_filtering(
    *,
    hate: Literal[0, 2, 4, 6] | None = None,
    violence: Literal[0, 2, 4, 6] | None = None,
    sexual: Literal[0, 2, 4, 6] | None = None,
    self_harm: Literal[0, 2, 4, 6] | None = None,
    prompt_shield: bool | None = None,
    directions: set[Literal["input", "output"]] | None = None,
    enabled: bool | None = None,
) -> None:
    """Override content filtering thresholds programmatically.

    Filtering is already activated by ``set_aicore_config()`` — this function
    is only needed to override specific thresholds at runtime. Any argument
    not provided retains its current value (from env vars or defaults).

    Args:
        hate: Azure Content Safety hate severity. 0=strict, 2=low+, 4=medium+ (default), 6=off.
        violence: Azure Content Safety violence severity.
        sexual: Azure Content Safety sexual severity.
        self_harm: Azure Content Safety self-harm severity.
        prompt_shield: Enable/disable jailbreak + indirect injection detection (input-only).
        directions: Set of directions to filter. Default is ``{"input", "output"}``.
        enabled: Set ``False`` to disable filtering entirely.

    Examples:
        Tighten two thresholds::

            set_filtering(self_harm=0, violence=0)

        Disable filtering entirely::

            set_filtering(enabled=False)
    """
    if enabled is False:
        _install(None)
        return

    # No args at all — just re-apply env-based config (respects ORCH_FILTER_ENABLED)
    if all(
        v is None
        for v in [hate, violence, sexual, self_harm, prompt_shield, directions, enabled]
    ):
        _install(FilteringModuleConfig.from_env())
        return

    # Some args provided — start from env-based config then override
    base = FilteringModuleConfig.from_env() or FilteringModuleConfig()

    # Build effective threshold — override only the provided args.
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
