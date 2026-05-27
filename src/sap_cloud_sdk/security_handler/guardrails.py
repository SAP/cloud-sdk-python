"""Security guardrails — composable, pluggable rule checks.

Extend Guardrail to add domain-specific rules without touching SecurityHandler.
"""

import re
from abc import ABC, abstractmethod

from .models import Severity, Violation, ViolationType


class Guardrail(ABC):
    """Pluggable guardrail interface. Implement check() to add custom rules."""

    @abstractmethod
    def check(self, text: str) -> list[Violation]: ...


class ForbiddenPatternGuardrail(Guardrail):
    """Block input matching any of the provided regex patterns (case-insensitive).

    Useful for domain-specific banned terms, competitor names, or internal
    code-words that should never appear in user input.
    """

    def __init__(
        self,
        patterns: list[str],
        severity: Severity = Severity.HIGH,
        description_prefix: str = "Forbidden pattern matched",
    ) -> None:
        self._compiled = [(re.compile(p, re.IGNORECASE), p) for p in patterns]
        self._severity = severity
        self._prefix = description_prefix

    def check(self, text: str) -> list[Violation]:
        violations: list[Violation] = []
        for pattern, raw in self._compiled:
            match = pattern.search(text)
            if match:
                violations.append(
                    Violation(
                        type=ViolationType.FORBIDDEN_PATTERN,
                        severity=self._severity,
                        description=f"{self._prefix}: {raw[:80]}",
                        matched_text=match.group(0)[:100],
                    )
                )
        return violations
