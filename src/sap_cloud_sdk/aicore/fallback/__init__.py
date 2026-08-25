"""Model-fallback subpackage for SAP AI Core Orchestration v2.

Re-exports the public surface defined in :mod:`.fallback`. Users should import
flat from :mod:`sap_cloud_sdk.aicore`; this package is the source of truth.
"""

from .fallback import FallbackConfig, FallbackModel, _apply_fallback, disable_fallbacks

__all__ = ["FallbackModel", "FallbackConfig", "disable_fallbacks", "_apply_fallback"]
