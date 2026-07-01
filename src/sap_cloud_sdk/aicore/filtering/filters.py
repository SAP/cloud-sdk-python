"""Public entry-point functions for SAP AI Core content filtering.

Two functions form the documented runtime API:

- :func:`set_filtering` — install a :class:`ContentFiltering` (or re-apply
  env-driven defaults when called with no args).
- :func:`disable_filtering` — restore the original LiteLLM transport.

Both are decorated with ``@record_metrics(Module.AICORE, …)`` for telemetry.
The package ``__init__`` re-exports them.

This module also defines :func:`_parse_input_filter_error`, the private
parser used by :mod:`sap_cloud_sdk.aicore.completion` to translate the
``litellm.APIConnectionError`` litellm raises for input-filter 400s into a
:class:`ContentFilteredError` before the exception reaches caller code.
"""

from __future__ import annotations

import json

from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation

from .models import ContentFiltering
from ._patch import _install
from .config import load_from_env
from .exceptions import ContentFilteredError


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
        _install(load_from_env())
        return
    _install(config)


@record_metrics(Module.AICORE, Operation.AICORE_DISABLE_FILTERING)
def disable_filtering() -> None:
    """Disable content filtering for SAP AI Core model calls.

    Restores the original ``litellm.GenAIHubOrchestrationConfig``.
    Idempotent — safe to call when filtering is already disabled.
    """
    _install(None)


def _parse_input_filter_error(exc: Exception) -> ContentFilteredError | None:
    """Internal: try to unwrap an input-filter rejection from a litellm exception.

    Returns a constructed :class:`ContentFilteredError` if the exception's
    string form contains the JSON shape produced by Azure Content Safety
    input-filter rejection, otherwise ``None``. Used by
    :mod:`sap_cloud_sdk.aicore.completion` to translate the
    ``litellm.APIConnectionError`` wrapping that ``raise_for_status()``
    produces before our transport patch sees the response.
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
    except (ValueError, KeyError, TypeError, AttributeError):
        # JSON parsing failure (ValueError from json.loads), missing dict key
        # (KeyError), wrong shape (TypeError from .get on non-dict), or attribute
        # access on a non-object (AttributeError) — all mean the exception
        # message isn't a content-filter rejection. Let other exception types
        # (logic bugs in ContentFilteredError construction) surface.
        return None
