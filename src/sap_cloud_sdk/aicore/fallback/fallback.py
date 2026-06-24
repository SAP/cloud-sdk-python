"""Public model-fallback API for SAP AI Core Orchestration v2.

Orchestration v2 supports module-configuration fallbacks: when the primary
configuration fails (model unsupported in region, 429, 408, or 5xx — and only
unsupported-model for streams), orchestration retries with the next preference.
See ``context/fallback.md``.

The litellm SAP provider already supports this: passing ``fallback_sap_modules``
through ``optional_params`` builds ``body["config"]["modules"]`` as a list.
This module is the SDK-side ergonomic layer: typed ``FallbackModel`` /
``FallbackConfig`` dataclasses, an env-driven ``from_env()`` builder, and the
``set_fallbacks()`` entry point that installs them into the shared
``OrchestrationPatchConfig`` patch (alongside any active filtering config).

Fallback is **opt-in**: ``set_aicore_config()`` does not enable it. Developers
must either call ``set_fallbacks(...)`` programmatically or set
``AICORE_FALLBACK_ENABLED=true`` and call ``set_fallbacks()`` (with no args).

The companion ``intermediate_failures`` field from the orchestration response
is surfaced as an attribute on the returned ``ModelResponse``. Non-streaming
only in v1 — streaming surfacing is deferred.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation

from ._patch import _install_fallback

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Env-var helpers (kept local — small, simple, no dependency on filtering)
# ---------------------------------------------------------------------------

_TRUTHY = frozenset({"true", "1", "yes"})


def _read_env_str(key: str, default: str = "") -> str:
    """Read a string env var. Trims whitespace. Returns ``default`` if absent."""
    raw = os.environ.get(key)
    return raw.strip() if raw is not None else default


def _read_env_bool(key: str, default: bool = False) -> bool:
    """Read a boolean env var.

    ``true``/``1``/``yes`` (case-insensitive) are True; anything else is False.
    Returns ``default`` if the variable is absent.
    """
    raw = os.environ.get(key)
    return (raw.strip().lower() in _TRUTHY) if raw is not None else default


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FallbackModel:
    """A single fallback preference.

    Args:
        model: Model name passed to orchestration (e.g. ``"sap/gpt-4o"``).
        params: Per-model params (``max_tokens``, ``temperature``, …). Optional.
            When omitted, the orchestration server falls back to its defaults
            for the model — it does NOT inherit the primary call's params.
        model_version: Specific model version. Defaults to ``"latest"`` on
            the server side when omitted.
    """

    model: str
    params: dict | None = None
    model_version: str | None = None

    def to_dict(self) -> dict:
        """Wire shape consumed by litellm's ``_build_prompt_module``.

        litellm pops ``model`` and ``model_version`` from the dict and treats
        everything else as model params. We keep this shape minimal.
        """
        result: dict = {"model": self.model}
        if self.model_version is not None:
            result["model_version"] = self.model_version
        if self.params:
            result.update(self.params)
        return result


@dataclass
class FallbackConfig:
    """Ordered list of fallback preferences.

    The orchestration server tries preferences in order; the first to succeed
    wins. Empty lists are accepted but have no effect (equivalent to no
    fallback).

    Args:
        models: Ordered list of :class:`FallbackModel` instances. Element 0
            is tried first after the primary call fails.
    """

    models: list[FallbackModel] = field(default_factory=list)

    def to_litellm_kwarg(self) -> list[dict]:
        """Build the list passed to litellm as ``fallback_sap_modules``."""
        return [m.to_dict() for m in self.models]

    @classmethod
    def from_env(cls) -> "FallbackConfig | None":
        """Build from ``AICORE_FALLBACK_*`` environment variables.

        Returns ``None`` when ``AICORE_FALLBACK_ENABLED`` is not truthy, or
        when enabled but neither ``AICORE_FALLBACK_CONFIG`` nor
        ``AICORE_FALLBACK_MODELS`` is set (treated as disabled — a warning is
        logged).

        Reads:
            AICORE_FALLBACK_ENABLED  (bool, default false) — opt-in switch
            AICORE_FALLBACK_CONFIG   (JSON string) — full per-model config,
                shape ``[{"model": ..., "params": {...}, "model_version": ...}]``.
                Takes precedence over MODELS when set. Malformed JSON raises.
            AICORE_FALLBACK_MODELS   (comma list) — simple model-only form.
                Each entry becomes ``FallbackModel(model=name)``.

        Raises:
            ValueError: If ``AICORE_FALLBACK_CONFIG`` is set but not valid
                JSON, or does not decode to a list of objects.
        """
        if not _read_env_bool("AICORE_FALLBACK_ENABLED", default=False):
            return None

        config_raw = _read_env_str("AICORE_FALLBACK_CONFIG")
        if config_raw:
            try:
                parsed = json.loads(config_raw)
            except ValueError as e:
                raise ValueError(
                    f"AICORE_FALLBACK_CONFIG must be valid JSON, got: {config_raw!r}"
                ) from e
            if not isinstance(parsed, list):
                raise ValueError(
                    f"AICORE_FALLBACK_CONFIG must decode to a list, got "
                    f"{type(parsed).__name__}"
                )
            models = [
                FallbackModel(
                    model=entry["model"],
                    params=entry.get("params"),
                    model_version=entry.get("model_version"),
                )
                for entry in parsed
            ]
            return cls(models=models)

        models_raw = _read_env_str("AICORE_FALLBACK_MODELS")
        if models_raw:
            names = [n.strip() for n in models_raw.split(",") if n.strip()]
            return cls(models=[FallbackModel(model=n) for n in names])

        logger.warning(
            "AICORE_FALLBACK_ENABLED is true but neither AICORE_FALLBACK_CONFIG "
            "nor AICORE_FALLBACK_MODELS is set; fallback remains inactive"
        )
        return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


@record_metrics(Module.AICORE, Operation.AICORE_SET_FALLBACKS)
def set_fallbacks(config: FallbackConfig | None = None) -> None:
    """Install a model-fallback configuration.

    Fallback is **opt-in**. ``set_aicore_config()`` does NOT activate it;
    the developer must call this function (or set the
    ``AICORE_FALLBACK_*`` env vars and call this function with no args).

    Args:
        config: A :class:`FallbackConfig` to install. If ``None`` (the
            default), reads ``AICORE_FALLBACK_*`` env vars via
            :meth:`FallbackConfig.from_env`. Pass ``None`` after an earlier
            call to clear an installed fallback at runtime.

    Examples:
        Programmatic::

            from sap_cloud_sdk.aicore import (
                FallbackConfig, FallbackModel, set_fallbacks,
            )

            set_fallbacks(FallbackConfig([
                FallbackModel(
                    model="sap/mistralai--mistral-small-instruct",
                    params={"temperature": 0.7, "max_tokens": 300},
                ),
            ]))

        From environment::

            import os
            from sap_cloud_sdk.aicore import set_fallbacks

            os.environ["AICORE_FALLBACK_ENABLED"] = "true"
            os.environ["AICORE_FALLBACK_MODELS"] = (
                "sap/mistralai--mistral-small-instruct"
            )
            set_fallbacks()
    """
    if config is None:
        _install_fallback(FallbackConfig.from_env())
        return
    _install_fallback(config)


__all__ = ["FallbackModel", "FallbackConfig", "set_fallbacks"]
