"""Filtering configuration dataclasses for SAP AI Core Orchestration v2."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

_TRUTHY = frozenset({"true", "1", "yes"})
_VALID_SEVERITIES = frozenset({0, 2, 4, 6})


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    return (raw.strip().lower() in _TRUTHY) if raw is not None else default


def _env_severity(key: str, default: int = 4) -> Literal[0, 2, 4, 6]:
    raw = _env(key, str(default))
    try:
        val = int(raw)
    except ValueError as e:
        raise ValueError(f"{key} must be one of 0/2/4/6, got {raw!r}") from e
    if val not in _VALID_SEVERITIES:
        raise ValueError(f"{key} must be one of 0/2/4/6, got {val}")
    return val  # type: ignore[return-value]


@dataclass
class ContentFilterConfig:
    """Azure Content Safety severity thresholds.

    Severity scale: 0 = strict (block any detected content),
    2 = low+, 4 = medium+ (default), 6 = off.

    Wire fields: filters[].config.hate/violence/sexual/self_harm
    """

    hate: Literal[0, 2, 4, 6] = 4
    violence: Literal[0, 2, 4, 6] = 4
    sexual: Literal[0, 2, 4, 6] = 4
    self_harm: Literal[0, 2, 4, 6] = 4


@dataclass
class PromptShieldConfig:
    """Prompt-attack (jailbreak + indirect injection) detection.

    Input-only. Wire field: filters[].config.prompt_shield
    """

    enabled: bool = True


@dataclass
class FilteringModuleConfig:
    """Content filtering for input and/or output of SAP AI Core model calls.

    Default: both directions active, threshold 4/4/4/4, prompt_shield=True.
    Construct directly or use ``from_env()`` to read ORCH_FILTER_* env vars.
    Call ``to_dict()`` to get the wire-format dict for the v2 request body.
    """

    input_filter: ContentFilterConfig | None = field(
        default_factory=ContentFilterConfig
    )
    output_filter: ContentFilterConfig | None = field(
        default_factory=ContentFilterConfig
    )
    prompt_shield: PromptShieldConfig | None = field(default_factory=PromptShieldConfig)

    @classmethod
    def from_env(cls) -> FilteringModuleConfig | None:
        """Build from ORCH_FILTER_* environment variables.

        Returns None when ORCH_FILTER_ENABLED=false, disabling filtering entirely.
        All variables are optional — safe defaults (threshold 4, prompt_shield=True)
        are used when not set.
        """
        if not _env_bool("ORCH_FILTER_ENABLED", default=True):
            return None

        directions_raw = _env("ORCH_FILTER_DIRECTIONS", "input,output")
        directions = {d.strip() for d in directions_raw.split(",") if d.strip()}

        thresholds = ContentFilterConfig(
            hate=_env_severity("ORCH_FILTER_HATE"),
            violence=_env_severity("ORCH_FILTER_VIOLENCE"),
            sexual=_env_severity("ORCH_FILTER_SEXUAL"),
            self_harm=_env_severity("ORCH_FILTER_SELF_HARM"),
        )
        prompt_shield = PromptShieldConfig(
            enabled=_env_bool("ORCH_FILTER_PROMPT_SHIELD", default=True)
        )

        return cls(
            input_filter=thresholds if "input" in directions else None,
            output_filter=thresholds if "output" in directions else None,
            prompt_shield=prompt_shield if "input" in directions else None,
        )

    def to_dict(self) -> dict:
        """Serialise to the v2 modules.filtering wire format.

        Wire shape (content-filtering.md L80-114):
            {
              "input":  {"filters": [{"type": "azure_content_safety", "config": {...}}]},
              "output": {"filters": [{"type": "azure_content_safety", "config": {...}}]}
            }
        prompt_shield is input-only (content-filtering.md L89).
        A direction key is omitted when its filter is None.
        """
        result: dict = {}

        if self.input_filter is not None:
            config: dict = {
                "hate": self.input_filter.hate,
                "violence": self.input_filter.violence,
                "sexual": self.input_filter.sexual,
                "self_harm": self.input_filter.self_harm,
            }
            if self.prompt_shield is not None and self.prompt_shield.enabled:
                config["prompt_shield"] = True
            result["input"] = {
                "filters": [{"type": "azure_content_safety", "config": config}]
            }

        if self.output_filter is not None:
            config = {
                "hate": self.output_filter.hate,
                "violence": self.output_filter.violence,
                "sexual": self.output_filter.sexual,
                "self_harm": self.output_filter.self_harm,
            }
            result["output"] = {
                "filters": [{"type": "azure_content_safety", "config": config}]
            }

        return result
