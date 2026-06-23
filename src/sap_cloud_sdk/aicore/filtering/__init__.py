"""SAP AI Core content filtering — Azure Content Safety + Prompt Shield.

Filtering is **enabled by default** when :func:`sap_cloud_sdk.aicore.set_aicore_config`
is called. No additional code is required. To override, build a
:class:`ContentFiltering` and pass it to :func:`set_filtering`; to turn
filtering off at runtime, use :func:`disable_filtering`; alternatively set
``AICORE_FILTER_*`` environment variables before :func:`set_aicore_config`.

See :mod:`sap_cloud_sdk.aicore` user guide for the documented public API.

This module is a thin re-export surface; the public API lives in
:mod:`.filters`. Internal pieces live in ``_litellm_patch`` (LiteLLM patch
and ``_install``) and ``exceptions``.
"""

from __future__ import annotations

from ._litellm_patch import extract_filter_blocked
from .exceptions import ContentFilteredError, OrchestrationError
from .filters import (
    AzureContentFilter,
    ContentFilter,
    ContentFiltering,
    InputFiltering,
    LlamaGuard38bFilter,
    OutputFiltering,
    Severity,
    disable_filtering,
    set_filtering,
)

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
