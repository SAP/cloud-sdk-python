"""SAP AI Core content filtering — Azure Content Safety + Prompt Shield.

Filtering is **enabled by default** when :func:`sap_cloud_sdk.aicore.set_aicore_config`
is called. No additional code is required. To override, build a
:class:`ContentFiltering` and pass it to :func:`set_filtering`; to turn
filtering off at runtime, use :func:`disable_filtering`; alternatively set
``AICORE_FILTER_*`` environment variables before :func:`set_aicore_config`.

See :mod:`sap_cloud_sdk.aicore` user guide for the documented public API.

Internal layout:

- :mod:`.models` — public dataclasses (``Severity``, ``ContentFilter``,
  ``AzureContentFilter``, ``LlamaGuard38bFilter``, ``InputFiltering``,
  ``OutputFiltering``, ``ContentFiltering``).
- :mod:`.config` — ``load_from_env`` + private env helpers.
- :mod:`._patch` — LiteLLM transport monkeypatch + ``_install``.
- :mod:`.filters` — public entry points (``set_filtering``, ``disable_filtering``,
  ``extract_filter_blocked``).
- :mod:`.exceptions` — error types.
"""

from __future__ import annotations

from .filters import (
    disable_filtering,
    extract_filter_blocked,  # noqa: F401 — deprecated, kept importable for back-compat
    set_filtering,
)
from .models import (
    AzureContentFilter,
    ContentFilter,
    ContentFiltering,
    InputFiltering,
    LlamaGuard38bFilter,
    OutputFiltering,
    Severity,
)
from .exceptions import ContentFilteredError, OrchestrationError

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
]
