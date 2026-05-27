"""Prompt injection detector.

Detects instruction-override, persona-redefinition, safety-bypass, system-prompt
extraction, and templating-token patterns derived from:
  - OWASP LLM Top 10 (LLM01 — Prompt Injection)
  - Common jailbreak taxonomies (DAN, role-play, mode-activation)
  - UCL security preamble injection-defense requirements

All violations are returned to the caller — blocking decisions live in SecurityHandler.
"""

import logging
import re
from typing import NamedTuple

from .models import Severity, Violation, ViolationType

logger = logging.getLogger(__name__)


class PatternRule(NamedTuple):
    pattern: str
    severity: Severity
    description: str


# ---------------------------------------------------------------------------
# Default injection detection rules
# ---------------------------------------------------------------------------

_DEFAULT_RULES: list[PatternRule] = [
    # --- Instruction override ---
    PatternRule(
        r"ignore\s+((?:previous|all|above|prior)\s+){1,3}(instructions?|prompts?|rules?|constraints?|context)",
        Severity.CRITICAL,
        "Instruction override attempt",
    ),
    PatternRule(
        r"(disregard|forget|bypass)\s+(your\s+)?(previous|all|above|prior)?\s*"
        r"(instructions?|rules?|constraints?|guidelines?)",
        Severity.CRITICAL,
        "Instruction override attempt",
    ),
    # --- Activation phrases / jailbreak modes ---
    PatternRule(r"\bjailbreak\b", Severity.HIGH, "Jailbreak keyword"),
    PatternRule(r"\bDAN\b", Severity.HIGH, "DAN jailbreak reference"),
    PatternRule(
        r"(developer|admin|god|unrestricted|unlocked|superuser)\s+"
        r"(mode|access|prompt|instructions?)",
        Severity.HIGH,
        "Privileged mode activation attempt",
    ),
    # --- Role / persona redefinition ---
    PatternRule(
        r"(act|pretend|imagine|suppose)\s+(you\s+)?(are|you'?re|as|to\s+be)\s+",
        Severity.HIGH,
        "Persona redefinition attempt",
    ),
    PatternRule(
        r"you\s+are\s+(now|a\s+new|no\s+longer)\s+",
        Severity.HIGH,
        "Identity override attempt",
    ),
    PatternRule(r"role[\s-]?play\s+as\s+", Severity.MEDIUM, "Role-play directive"),
    # --- Constraint / safety bypass ---
    PatternRule(
        r"(reset|unlock|remove|disable|override|bypass)\s+(your\s+)?"
        r"(safety|restrictions?|constraints?|instructions?|rules?|filters?|guardrails?)",
        Severity.HIGH,
        "Safety bypass attempt",
    ),
    PatternRule(
        r"(new\s+)?(paradigm|context|persona|directive)\s*(:\s*|is\s+now\b|begins?\b)",
        Severity.MEDIUM,
        "Context redefinition attempt",
    ),
    # --- System prompt extraction ---
    PatternRule(
        r"(reveal|show(?:\s+me)?|print|output|display|repeat|share|tell\s+me|what\s+(?:is|are))\s+"
        r"(your\s+)?(system\s+)?(prompt|instructions?|rules?|directives?|preamble)",
        Severity.HIGH,
        "System prompt extraction attempt",
    ),
    # --- Response prefix injection ---
    PatternRule(
        r"(start|begin)\s+(your\s+)?(response\s+)?(with|by\s+saying|with\s+the\s+words?)\s+[\"']",
        Severity.LOW,
        "Response prefix injection",
    ),
]

# Templating / shell-execution tokens (UCL preamble § Injection defenses)
_TEMPLATING_RULES: list[PatternRule] = [
    PatternRule(r"\$\{[^}]{0,200}\}", Severity.MEDIUM, "Template token ${...}"),
    PatternRule(r"\{\{[^}]{0,200}\}\}", Severity.MEDIUM, "Template token {{...}}"),
    PatternRule(r"<<[^>]{0,200}>>", Severity.MEDIUM, "Template token <<...>>"),
    PatternRule(r"#!\s*\S+", Severity.MEDIUM, "Shell-command token #!"),
]


class InjectionDetector:
    """Scan text for prompt injection patterns.

    Returns all matching violations — the caller (SecurityHandler) decides
    the blocking threshold.
    """

    def __init__(
        self,
        extra_rules: list[PatternRule] | None = None,
        include_templating_checks: bool = True,
    ) -> None:
        rules: list[PatternRule] = list(_DEFAULT_RULES)
        if include_templating_checks:
            rules.extend(_TEMPLATING_RULES)
        if extra_rules:
            rules.extend(extra_rules)
        self._compiled = [
            (re.compile(r.pattern, re.IGNORECASE), r.severity, r.description)
            for r in rules
        ]

    def detect(self, text: str) -> list[Violation]:
        """Return all injection violations found in text. Does not modify text."""
        violations: list[Violation] = []
        for pattern, severity, description in self._compiled:
            match = pattern.search(text)
            if match:
                violations.append(
                    Violation(
                        type=ViolationType.INJECTION_ATTEMPT,
                        severity=severity,
                        description=description,
                        matched_text=match.group(0)[:100],
                    )
                )
        return violations
