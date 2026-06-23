"""Public content-filtering API for SAP AI Core Orchestration v2.

Everything related to filtering lives in this single module:

- ``Severity`` enum (threshold values).
- Filter providers: ``ContentFilter`` (base), ``AzureContentFilter``,
  ``LlamaGuard38bFilter``.
- Direction containers: ``InputFiltering``, ``OutputFiltering``,
  ``ContentFiltering``.
- Entry points: ``set_filtering()``, ``disable_filtering()``.
- LiteLLM patch: ``FilteringOrchestrationConfig``, ``_install()``.
- Exception parser: ``extract_filter_blocked()``.

The package's ``__init__`` re-exports the public names so users can import
flat from :mod:`sap_cloud_sdk.aicore`; this module is the source of truth.

Internal-only error types live in :mod:`.exceptions`.
"""

from __future__ import annotations

import json
import logging
import os
from enum import IntEnum
from typing import Any

import litellm
from litellm.llms.sap.chat.transformation import GenAIHubOrchestrationConfig
from litellm.types.utils import ModelResponse

from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation

from .exceptions import ContentFilteredError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed env-var helpers (used by ContentFiltering.from_env)
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


def _read_env_choice(key: str, choices: set[int], default: int) -> int:
    """Read an int env var, validate membership in ``choices``.

    Returns ``default`` when the variable is absent. Raises ``ValueError`` if
    the value cannot be parsed as ``int`` or is not in ``choices``.
    """
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError as e:
        raise ValueError(f"{key} must be one of {sorted(choices)}, got {raw!r}") from e
    if value not in choices:
        raise ValueError(f"{key} must be one of {sorted(choices)}, got {value}")
    return value


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
        if not _read_env_bool("AICORE_FILTER_ENABLED", default=True):
            return None

        directions_raw = _read_env_str("AICORE_FILTER_DIRECTIONS", "input,output")
        directions = {d.strip() for d in directions_raw.split(",") if d.strip()}

        hate = Severity(
            _read_env_choice("AICORE_FILTER_HATE", _VALID_SEVERITIES, default=4)
        )
        violence = Severity(
            _read_env_choice("AICORE_FILTER_VIOLENCE", _VALID_SEVERITIES, default=4)
        )
        sexual = Severity(
            _read_env_choice("AICORE_FILTER_SEXUAL", _VALID_SEVERITIES, default=4)
        )
        self_harm = Severity(
            _read_env_choice("AICORE_FILTER_SELF_HARM", _VALID_SEVERITIES, default=4)
        )
        prompt_shield = _read_env_bool("AICORE_FILTER_PROMPT_SHIELD", default=True)

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
# LiteLLM transport patch
# ---------------------------------------------------------------------------
#
# Patches ``litellm.GenAIHubOrchestrationConfig`` with a subclass that:
# - Injects ``modules.filtering`` into every v2 completion request body
# - Detects filter rejections in responses and raises ``ContentFilteredError``
#
# The patch is applied by ``_install(cfg)`` and undone by ``_install(None)``.
# It is idempotent — calling it multiple times with the same config is safe.
#
# Two filter rejection shapes (from the v2 API) are handled:
# - Input rejection: HTTP 4xx, ``error.location`` startswith
#   ``"Filtering Module - Input Filter"`` (content-filtering.md L130-162)
# - Output rejection: HTTP 200, ``finish_reason == "content_filter"``,
#   empty ``message.content`` (content-filtering.md L234-303)
#
# LiteLLM's ``raise_for_status()`` turns 4xx responses into
# ``httpx.HTTPStatusError`` before ``transform_response`` is reached,
# so input-filter 400s arrive wrapped in a ``litellm.APIConnectionError``
# with the JSON embedded in the exception message.
# ``extract_filter_blocked()`` handles that case.

# Keep the original so _install(None) can restore it.
_ORIGINAL_CONFIG = litellm.GenAIHubOrchestrationConfig

_active_cfg: Any = None  # ContentFiltering | None, stored at module level


class FilteringOrchestrationConfig(GenAIHubOrchestrationConfig):
    """GenAIHubOrchestrationConfig subclass that injects content filtering."""

    def transform_request(
        self,
        model: str,
        messages: list,
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        body = super().transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        if _active_cfg is None:
            return body

        filtering_dict = _active_cfg.to_dict()
        if not filtering_dict:
            return body

        modules = body["config"]["modules"]
        if isinstance(modules, list):
            # Fallback mode (list of configs) — inject into primary config only.
            modules[0]["filtering"] = filtering_dict
        else:
            modules["filtering"] = filtering_dict

        return body

    def transform_response(
        self,
        model: str,
        raw_response: Any,
        model_response: ModelResponse,
        logging_obj: Any,
        request_data: dict,
        messages: list,
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: str | None = None,
        json_mode: bool | None = None,
    ) -> ModelResponse:
        status = raw_response.status_code

        # Input-filter rejection (HTTP 4xx).
        # content-filtering.md L130-162: error.location identifies the filter module.
        if 400 <= status < 500:
            try:
                body = raw_response.json()
            except ValueError:
                # Response wasn't JSON (gateway error page, plain-text 5xx,
                # truncated body, etc.) — not a filter rejection, fall through
                # to LiteLLM's default handling.
                body = None
            if body is not None:
                err = body.get("error", {})
                if (err.get("location") or "").startswith(
                    "Filtering Module - Input Filter"
                ):
                    data = (
                        err.get("intermediate_results", {})
                        .get("input_filtering", {})
                        .get("data", {})
                    )
                    raise ContentFilteredError(
                        direction="input",
                        details=data,
                        request_id=err.get("request_id"),
                    )

        # Output-filter rejection (HTTP 200 + finish_reason == "content_filter").
        # content-filtering.md L234-303: message.content is "" (empty, not absent).
        if status == 200:
            try:
                payload = raw_response.json()
            except ValueError:
                # Response wasn't JSON — pass through to LiteLLM.
                payload = None
            if payload is not None:
                choices = (payload.get("final_result") or {}).get("choices") or []
                if choices and choices[0].get("finish_reason") == "content_filter":
                    data = (
                        payload.get("intermediate_results", {})
                        .get("output_filtering", {})
                        .get("data", {})
                    )
                    raise ContentFilteredError(
                        direction="output",
                        details=data,
                        request_id=payload.get("request_id"),
                    )

        return super().transform_response(
            model=model,
            raw_response=raw_response,
            model_response=model_response,
            logging_obj=logging_obj,
            request_data=request_data,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            encoding=encoding,
            api_key=api_key,
            json_mode=json_mode,
        )


def _install(cfg: Any) -> None:  # cfg: ContentFiltering | None
    """Patch litellm.GenAIHubOrchestrationConfig. Idempotent.

    cfg=None restores the original config and disables filtering.
    """
    global _active_cfg
    _active_cfg = cfg
    if cfg is None:
        litellm.GenAIHubOrchestrationConfig = _ORIGINAL_CONFIG
        logger.debug("content filtering disabled")
    else:
        litellm.GenAIHubOrchestrationConfig = FilteringOrchestrationConfig
        logger.info("content filtering active (FilteringOrchestrationConfig)")


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


@record_metrics(Module.AICORE, Operation.AICORE_EXTRACT_FILTER_BLOCKED)
def extract_filter_blocked(exc: Exception) -> ContentFilteredError | None:
    """Parse a LiteLLM APIConnectionError for an input-filter rejection.

    When Azure Content Safety blocks the input, LiteLLM's ``raise_for_status()``
    converts the 400 into an ``httpx.HTTPStatusError``, which is then wrapped
    into a ``litellm.APIConnectionError`` with the original JSON embedded in
    the exception message string. This function extracts it.

    Returns None if the exception is not a content-filter rejection.

    A telemetry event is emitted on every call, including calls where the
    exception was not a content-filter rejection (returns ``None``).
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
    except Exception:
        return None
