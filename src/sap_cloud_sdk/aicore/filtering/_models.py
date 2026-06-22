"""Filtering configuration dataclasses for SAP AI Core Orchestration v2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from sap_cloud_sdk.core.env import read_env_bool, read_env_choice, read_env_str


class Severity(IntEnum):
    """Azure Content Safety severity threshold for filter rejection.

    Lower values are stricter. ``STRICT`` blocks any detected content;
    ``OFF`` disables the filter. ``IntEnum`` so members serialise as their
    int value (``json.dumps(Severity.MEDIUM) == "4"``) — the wire format
    is unchanged from the previous ``Literal[0, 2, 4, 6]`` typing.
    """

    STRICT = 0
    LOW = 2
    MEDIUM = 4
    OFF = 6


_VALID_SEVERITIES: set[int] = {s.value for s in Severity}


@dataclass
class ContentFilterConfig:
    """Azure Content Safety severity thresholds.

    Wire fields: ``filters[].config.hate / violence / sexual / self_harm``.
    """

    hate: Severity = Severity.MEDIUM
    violence: Severity = Severity.MEDIUM
    sexual: Severity = Severity.MEDIUM
    self_harm: Severity = Severity.MEDIUM


@dataclass
class PromptShieldConfig:
    """Prompt-attack (jailbreak + indirect injection) detection.

    Input-only. Wire field: ``filters[].config.prompt_shield``.
    """

    enabled: bool = True


@dataclass
class FilteringModuleConfig:
    """Content filtering for input and/or output of SAP AI Core model calls.

    Default: both directions active, threshold ``MEDIUM`` on every category,
    ``prompt_shield=True``. Construct directly or use :meth:`from_env` to
    read ``AICORE_FILTER_*`` environment variables. Call :meth:`to_dict` to
    get the wire-format dict for the v2 request body.
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
        """Build from ``AICORE_FILTER_*`` environment variables.

        Returns ``None`` when ``AICORE_FILTER_ENABLED=false``, disabling
        filtering entirely. All variables are optional — safe defaults
        (threshold ``MEDIUM``, ``prompt_shield=True``) are used when not set.
        """
        if not read_env_bool("AICORE_FILTER_ENABLED", default=True):
            return None

        directions_raw = read_env_str("AICORE_FILTER_DIRECTIONS", "input,output")
        directions = {d.strip() for d in directions_raw.split(",") if d.strip()}

        thresholds = ContentFilterConfig(
            hate=Severity(
                read_env_choice("AICORE_FILTER_HATE", _VALID_SEVERITIES, default=4)
            ),
            violence=Severity(
                read_env_choice("AICORE_FILTER_VIOLENCE", _VALID_SEVERITIES, default=4)
            ),
            sexual=Severity(
                read_env_choice("AICORE_FILTER_SEXUAL", _VALID_SEVERITIES, default=4)
            ),
            self_harm=Severity(
                read_env_choice("AICORE_FILTER_SELF_HARM", _VALID_SEVERITIES, default=4)
            ),
        )
        prompt_shield = PromptShieldConfig(
            enabled=read_env_bool("AICORE_FILTER_PROMPT_SHIELD", default=True)
        )

        return cls(
            input_filter=thresholds if "input" in directions else None,
            output_filter=thresholds if "output" in directions else None,
            prompt_shield=prompt_shield if "input" in directions else None,
        )

    def to_dict(self) -> dict:
        """Serialise to the v2 ``modules.filtering`` wire format.

        Wire shape::

            {
              "input":  {"filters": [{"type": "azure_content_safety", "config": {...}}]},
              "output": {"filters": [{"type": "azure_content_safety", "config": {...}}]}
            }

        ``prompt_shield`` is input-only. A direction key is omitted when its
        filter is ``None``.
        """
        result: dict = {}

        if self.input_filter is not None:
            config: dict = {
                "hate": int(self.input_filter.hate),
                "violence": int(self.input_filter.violence),
                "sexual": int(self.input_filter.sexual),
                "self_harm": int(self.input_filter.self_harm),
            }
            if self.prompt_shield is not None and self.prompt_shield.enabled:
                config["prompt_shield"] = True
            result["input"] = {
                "filters": [{"type": "azure_content_safety", "config": config}]
            }

        if self.output_filter is not None:
            config = {
                "hate": int(self.output_filter.hate),
                "violence": int(self.output_filter.violence),
                "sexual": int(self.output_filter.sexual),
                "self_harm": int(self.output_filter.self_harm),
            }
            result["output"] = {
                "filters": [{"type": "azure_content_safety", "config": config}]
            }

        return result
