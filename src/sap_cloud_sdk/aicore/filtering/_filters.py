"""Content-filter provider classes and the Severity enum.

This module owns:

- ``Severity`` — Azure Content Safety threshold enum, consumed by
  :class:`AzureContentFilter`.
- ``ContentFilter`` — abstract base for provider implementations.
- ``AzureContentFilter`` / ``LlamaGuard38bFilter`` — concrete providers.

Direction containers (:class:`InputFiltering`, :class:`OutputFiltering`,
:class:`ContentFiltering`) live in :mod:`._modules`.
"""

from __future__ import annotations

from enum import IntEnum


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
