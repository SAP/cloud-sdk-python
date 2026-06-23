"""Public content-filtering API for SAP AI Core Orchestration v2.

Everything a caller needs to configure filtering lives here:

- ``Severity`` enum (threshold values).
- Filter providers: ``ContentFilter`` (base), ``AzureContentFilter``,
  ``LlamaGuard38bFilter``.
- Direction containers: ``InputFiltering``, ``OutputFiltering``,
  ``ContentFiltering``.
- Entry points: ``set_filtering()``, ``disable_filtering()``.

The package's ``__init__`` re-exports these names so users can import flat
from :mod:`sap_cloud_sdk.aicore`; this module is the source of truth for
the public surface.

Internal-only pieces — ``_litellm_patch`` (LiteLLM monkeypatch and
``_install``) and ``exceptions`` (error types) — live in sibling files.
"""

from __future__ import annotations

from enum import IntEnum

from sap_cloud_sdk.core.env import read_env_bool, read_env_choice, read_env_str
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation

from ._litellm_patch import _install


# ---------------------------------------------------------------------------
# Severity enum
# ---------------------------------------------------------------------------


class Severity(IntEnum):
    """Azure Content Safety severity threshold for filter rejection.

    Lower values are stricter. ``STRICT`` blocks any detected content;
    ``OFF`` disables the filter. ``IntEnum`` so members serialise as their
    int value (``json.dumps(Severity.MEDIUM) == "4"``).
    """

    STRICT = 0
    LOW = 2
    MEDIUM = 4
    OFF = 6


_VALID_SEVERITIES: set[int] = {s.value for s in Severity}


# ---------------------------------------------------------------------------
# Filter providers
# ---------------------------------------------------------------------------


class ContentFilter:
    """Abstract base for content-filter providers.

    Subclasses must populate ``self.provider`` (str) and ``self.config`` (dict)
    in their ``__init__``. The base ``to_dict()`` emits the wire format
    ``{"type": provider, "config": config}``. Subclass to add new providers.
    """

    provider: str
    config: dict

    def to_dict(self) -> dict:
        return {"type": self.provider, "config": self.config}


class AzureContentFilter(ContentFilter):
    """Azure Content Safety filter.

    Configures category thresholds for Azure-backed content moderation, plus
    the input-only Prompt Shield (jailbreak + indirect-injection detection).

    Args:
        hate: Severity threshold for hate content.
        violence: Severity threshold for violent content.
        sexual: Severity threshold for sexual content.
        self_harm: Severity threshold for self-harm content.
        prompt_shield: Enable Prompt Shield. Input-only — setting it on output
            filters has no effect server-side but is silently accepted.

    All threshold args accept either a ``Severity`` enum member or a raw
    ``int`` in ``{0, 2, 4, 6}``. Raw ints are validated via the ``Severity``
    constructor (raises ``ValueError`` for an out-of-set value).
    """

    def __init__(
        self,
        *,
        hate: Severity | int = Severity.MEDIUM,
        violence: Severity | int = Severity.MEDIUM,
        sexual: Severity | int = Severity.MEDIUM,
        self_harm: Severity | int = Severity.MEDIUM,
        prompt_shield: bool = False,
    ) -> None:
        config: dict = {
            "hate": int(Severity(hate)),
            "violence": int(Severity(violence)),
            "sexual": int(Severity(sexual)),
            "self_harm": int(Severity(self_harm)),
        }
        if prompt_shield:
            config["prompt_shield"] = True
        self.provider = "azure_content_safety"
        self.config = config


class LlamaGuard38bFilter(ContentFilter):
    """Llama Guard 3 8B filter (Llama-3.1-8B fine-tuned for safety classification).

    Each parameter is a boolean toggle for a single category. Setting a flag
    to ``True`` instructs the server to block content matching that category.
    All flags default to ``False``.

    Args:
        violent_crimes: Block responses that enable, encourage, or endorse violent crimes.
        non_violent_crimes: Block responses that enable, encourage, or endorse non-violent crimes.
        sex_crimes: Block responses that enable, encourage, or endorse sex-related crimes.
        child_exploitation: Block responses that contain or endorse sexual abuse of children.
        defamation: Block responses that are verifiably false and damaging to a living person.
        specialized_advice: Block responses containing specialized financial, medical, or legal advice.
        privacy: Block responses containing sensitive or nonpublic personal information.
        intellectual_property: Block responses that may violate third-party IP rights.
        indiscriminate_weapons: Block responses that enable or endorse indiscriminate-weapon creation.
        hate: Block responses that demean or dehumanize based on personal characteristics.
        self_harm: Block responses that enable, encourage, or endorse intentional self-harm.
        sexual_content: Block responses containing erotica.
        elections: Block responses containing factually incorrect information about elections.
        code_interpreter_abuse: Block responses that seek to abuse code interpreters.
    """

    def __init__(
        self,
        *,
        violent_crimes: bool = False,
        non_violent_crimes: bool = False,
        sex_crimes: bool = False,
        child_exploitation: bool = False,
        defamation: bool = False,
        specialized_advice: bool = False,
        privacy: bool = False,
        intellectual_property: bool = False,
        indiscriminate_weapons: bool = False,
        hate: bool = False,
        self_harm: bool = False,
        sexual_content: bool = False,
        elections: bool = False,
        code_interpreter_abuse: bool = False,
    ) -> None:
        self.provider = "llama_guard_3_8b"
        self.config = {
            "violent_crimes": violent_crimes,
            "non_violent_crimes": non_violent_crimes,
            "sex_crimes": sex_crimes,
            "child_exploitation": child_exploitation,
            "defamation": defamation,
            "specialized_advice": specialized_advice,
            "privacy": privacy,
            "intellectual_property": intellectual_property,
            "indiscriminate_weapons": indiscriminate_weapons,
            "hate": hate,
            "self_harm": self_harm,
            "sexual_content": sexual_content,
            "elections": elections,
            "code_interpreter_abuse": code_interpreter_abuse,
        }


# ---------------------------------------------------------------------------
# Direction containers + top-level configuration
# ---------------------------------------------------------------------------


class InputFiltering:
    """Input-direction filter stack.

    Args:
        filters: Ordered list of ``ContentFilter`` instances. The server applies
            them in order; the first to reject wins.
    """

    def __init__(self, filters: list[ContentFilter]) -> None:
        self.filters = filters

    def to_dict(self) -> dict:
        return {"filters": [f.to_dict() for f in self.filters]}


class OutputFiltering:
    """Output-direction filter stack.

    Args:
        filters: Ordered list of ``ContentFilter`` instances.
        stream_options: Optional module-specific streaming options. Passed
            through verbatim when set; omitted from the wire payload when
            ``None``.
    """

    def __init__(
        self,
        filters: list[ContentFilter],
        stream_options: dict | None = None,
    ) -> None:
        self.filters = filters
        self.stream_options = stream_options

    def to_dict(self) -> dict:
        result: dict = {"filters": [f.to_dict() for f in self.filters]}
        if self.stream_options:
            result["stream_options"] = self.stream_options
        return result


class ContentFiltering:
    """Complete content-filtering configuration for a single set_filtering call.

    Args:
        input_filtering: Filters applied to the user prompt before the model sees it.
        output_filtering: Filters applied to the model response before the user sees it.

    A direction key is omitted from the wire payload when its corresponding
    argument is ``None``.
    """

    def __init__(
        self,
        input_filtering: InputFiltering | None = None,
        output_filtering: OutputFiltering | None = None,
    ) -> None:
        self.input_filtering = input_filtering
        self.output_filtering = output_filtering

    def to_dict(self) -> dict:
        result: dict = {}
        if self.input_filtering is not None:
            result["input"] = self.input_filtering.to_dict()
        if self.output_filtering is not None:
            result["output"] = self.output_filtering.to_dict()
        return result

    @classmethod
    def from_env(cls) -> "ContentFiltering | None":
        """Build from ``AICORE_FILTER_*`` environment variables.

        Returns ``None`` when ``AICORE_FILTER_ENABLED=false``, disabling
        filtering entirely. Constructs a single ``AzureContentFilter`` per
        direction (LlamaGuard is opt-in via explicit programmatic config).

        Reads:
            AICORE_FILTER_ENABLED       (bool, default true)
            AICORE_FILTER_DIRECTIONS    (comma list, default "input,output")
            AICORE_FILTER_HATE          (int 0/2/4/6, default 4)
            AICORE_FILTER_VIOLENCE      (int 0/2/4/6, default 4)
            AICORE_FILTER_SEXUAL        (int 0/2/4/6, default 4)
            AICORE_FILTER_SELF_HARM     (int 0/2/4/6, default 4)
            AICORE_FILTER_PROMPT_SHIELD (bool, default true) — input-only
        """
        if not read_env_bool("AICORE_FILTER_ENABLED", default=True):
            return None

        directions_raw = read_env_str("AICORE_FILTER_DIRECTIONS", "input,output")
        directions = {d.strip() for d in directions_raw.split(",") if d.strip()}

        hate = Severity(
            read_env_choice("AICORE_FILTER_HATE", _VALID_SEVERITIES, default=4)
        )
        violence = Severity(
            read_env_choice("AICORE_FILTER_VIOLENCE", _VALID_SEVERITIES, default=4)
        )
        sexual = Severity(
            read_env_choice("AICORE_FILTER_SEXUAL", _VALID_SEVERITIES, default=4)
        )
        self_harm = Severity(
            read_env_choice("AICORE_FILTER_SELF_HARM", _VALID_SEVERITIES, default=4)
        )
        prompt_shield = read_env_bool("AICORE_FILTER_PROMPT_SHIELD", default=True)

        input_filtering: InputFiltering | None = None
        if "input" in directions:
            input_filtering = InputFiltering(
                filters=[
                    AzureContentFilter(
                        hate=hate,
                        violence=violence,
                        sexual=sexual,
                        self_harm=self_harm,
                        prompt_shield=prompt_shield,
                    )
                ]
            )

        output_filtering: OutputFiltering | None = None
        if "output" in directions:
            output_filtering = OutputFiltering(
                filters=[
                    AzureContentFilter(
                        hate=hate,
                        violence=violence,
                        sexual=sexual,
                        self_harm=self_harm,
                    )
                ]
            )

        return cls(
            input_filtering=input_filtering,
            output_filtering=output_filtering,
        )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


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
