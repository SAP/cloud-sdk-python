"""Public function bodies for the filtering sub-package.

Both ``set_filtering`` and ``disable_filtering`` are re-exported from
:mod:`sap_cloud_sdk.aicore.filtering` and :mod:`sap_cloud_sdk.aicore`. They
live here (rather than in ``__init__.py``) so the package's ``__init__``
stays a thin re-export surface.
"""

from __future__ import annotations

from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation

from ._litellm_patch import _install
from ._modules import ContentFiltering


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
