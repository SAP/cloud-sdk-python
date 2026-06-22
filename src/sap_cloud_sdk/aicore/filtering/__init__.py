"""SAP AI Core content filtering — Azure Content Safety + Prompt Shield.

Filtering is **enabled by default** when :func:`sap_cloud_sdk.aicore.set_aicore_config`
is called. No additional code is required. To override, build a
:class:`ContentFiltering` and pass it to :func:`set_filtering`; to turn
filtering off at runtime, use :func:`disable_filtering`; alternatively set
``AICORE_FILTER_*`` environment variables before :func:`set_aicore_config`.

See :mod:`sap_cloud_sdk.aicore` user guide for the documented public API.
"""

from __future__ import annotations

import logging

from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation

from ._filters import AzureContentFilter, ContentFilter, LlamaGuard38bFilter
from ._litellm_patch import _install, extract_filter_blocked
from ._models import Severity
from ._modules import ContentFiltering, InputFiltering, OutputFiltering
from .exceptions import ContentFilteredError, OrchestrationError

logger = logging.getLogger(__name__)

__all__ = [
    "set_filtering",
    "disable_filtering",
    "ContentFiltering",
    "InputFiltering",
    "OutputFiltering",
    "AzureContentFilter",
    "LlamaGuard38bFilter",
    "ContentFilter",
    "Severity",
    "ContentFilteredError",
    "OrchestrationError",
    "extract_filter_blocked",
]


@record_metrics(Module.AICORE, Operation.AICORE_SET_FILTERING)
def set_filtering(config: ContentFiltering | None = None) -> None:
    """Install a content-filtering configuration.

    Args:
        config: A :class:`ContentFiltering` to install. If ``None`` (the
            default), re-applies env-var-driven defaults — respects
            ``AICORE_FILTER_ENABLED=false`` to keep filtering off. An
            explicit non-``None`` config always activates filtering, even
            when the env var would have disabled it.

    Examples:
        Activate strict input filtering with Prompt Shield::

            set_filtering(ContentFiltering(
                input_filtering=InputFiltering(filters=[
                    AzureContentFilter(
                        hate=Severity.STRICT,
                        violence=Severity.STRICT,
                        sexual=Severity.STRICT,
                        self_harm=Severity.STRICT,
                        prompt_shield=True,
                    ),
                ]),
            ))

        Re-apply env-based config after changing variables::

            set_filtering()
    """
    if config is None:
        _install(ContentFiltering.from_env())
        return
    _install(config)


@record_metrics(Module.AICORE, Operation.AICORE_DISABLE_FILTERING)
def disable_filtering() -> None:
    """Disable content filtering for SAP AI Core model calls.

    Restores the original ``litellm.GenAIHubOrchestrationConfig``.
    Idempotent — safe to call when filtering is already disabled.
    """
    _install(None)
