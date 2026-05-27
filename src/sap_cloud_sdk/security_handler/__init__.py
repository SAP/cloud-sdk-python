"""security_handler — Generic LLM security utilities for agent pipelines.

Provides a composable pre-LLM gate covering:
  - Input sanitization (control chars, whitespace, length)
  - Prompt injection detection (instruction override, persona redefinition,
    safety bypass, system prompt extraction, templating tokens)
  - Pluggable security guardrails (forbidden patterns, custom rules)

Typical usage::

    from sap_cloud_sdk.security_handler import SecurityHandler

    handler = SecurityHandler()
    result = handler.scan(user_input)
    if result.is_blocked:
        raise ValueError(result.violations[0].description)
    process(result.sanitized_text)

With custom config::

    from sap_cloud_sdk.security_handler import SecurityHandler, SecurityConfig, Severity

    handler = SecurityHandler(SecurityConfig(
        min_blocking_severity=Severity.HIGH,
        custom_forbidden_patterns=[r"competitor_name"],
    ))
"""

import logging
from dataclasses import dataclass, field

from .guardrails import ForbiddenPatternGuardrail, Guardrail
from .injection_detector import InjectionDetector, PatternRule
from .models import ScanResult, Severity, Violation, ViolationType
from .sanitizer import InputTooLongError, MAX_INPUT_LENGTH, escape_xml_tags, sanitize

logger = logging.getLogger(__name__)

_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


@dataclass
class SecurityConfig:
    """Configuration for SecurityHandler.

    Attributes:
        max_input_length: Hard cap on input length. Inputs exceeding this are
            blocked immediately without further scanning.
        min_blocking_severity: Violations at or above this severity cause
            is_blocked=True. Defaults to MEDIUM.
        injection_detection: Enable/disable the built-in injection detector.
        templating_token_detection: Enable/disable ${...}, {{...}}, <<...>> checks.
        custom_forbidden_patterns: Extra case-insensitive regex patterns to treat
            as forbidden (evaluated as a ForbiddenPatternGuardrail at HIGH severity).
        extra_injection_rules: Additional PatternRule instances appended to the
            built-in injection rule set.
        custom_guardrails: Fully custom Guardrail implementations.
    """

    max_input_length: int = MAX_INPUT_LENGTH
    min_blocking_severity: Severity = Severity.MEDIUM
    injection_detection: bool = True
    templating_token_detection: bool = True
    custom_forbidden_patterns: list[str] = field(default_factory=list)
    extra_injection_rules: list[PatternRule] = field(default_factory=list)
    custom_guardrails: list[Guardrail] = field(default_factory=list)


class SecurityHandler:
    """Orchestrates sanitization, injection detection, and guardrail enforcement.

    Designed as a pre-LLM gate: call scan() on every user message before it
    reaches any prompt template or agent node.
    """

    def __init__(self, config: SecurityConfig | None = None) -> None:
        self.config = config or SecurityConfig()

        self._detector = (
            InjectionDetector(
                extra_rules=self.config.extra_injection_rules,
                include_templating_checks=self.config.templating_token_detection,
            )
            if self.config.injection_detection
            else None
        )

        self._guardrails: list[Guardrail] = []
        if self.config.custom_forbidden_patterns:
            self._guardrails.append(
                ForbiddenPatternGuardrail(self.config.custom_forbidden_patterns)
            )
        self._guardrails.extend(self.config.custom_guardrails)

    def scan(self, text: str | None) -> ScanResult:
        """Sanitize and scan text for security violations.

        Always returns a ScanResult. sanitized_text is safe to embed in a prompt.
        is_blocked is True when any violation meets or exceeds
        config.min_blocking_severity.
        """
        if not text:
            return ScanResult(original_text=text or "", sanitized_text=text or "")

        violations: list[Violation] = []

        # 1. Sanitize — strips control chars, normalises whitespace, enforces length.
        try:
            sanitized, san_violations = sanitize(text, self.config.max_input_length)
            violations.extend(san_violations)
        except InputTooLongError as exc:
            violations.append(
                Violation(
                    type=ViolationType.INPUT_TOO_LONG,
                    severity=Severity.HIGH,
                    description=str(exc),
                )
            )
            return ScanResult(
                original_text=text,
                sanitized_text=text[: self.config.max_input_length],
                violations=violations,
                is_blocked=True,
            )

        sanitized = sanitized or ""

        # 2. Injection detection.
        if self._detector and sanitized:
            violations.extend(self._detector.detect(sanitized))

        # 3. Custom guardrails.
        for guardrail in self._guardrails:
            if sanitized:
                violations.extend(guardrail.check(sanitized))

        # 4. Block decision.
        threshold = _SEVERITY_ORDER[self.config.min_blocking_severity]
        is_blocked = any(_SEVERITY_ORDER[v.severity] >= threshold for v in violations)

        if is_blocked:
            logger.warning(
                "SecurityHandler blocked input — %d violation(s): %s",
                len(violations),
                [v.description for v in violations],
            )

        return ScanResult(
            original_text=text,
            sanitized_text=sanitized,
            violations=violations,
            is_blocked=is_blocked,
        )


__all__ = [
    "SecurityHandler",
    "SecurityConfig",
    "ScanResult",
    "Violation",
    "Severity",
    "ViolationType",
    "Guardrail",
    "ForbiddenPatternGuardrail",
    "InjectionDetector",
    "PatternRule",
    "InputTooLongError",
    "escape_xml_tags",
]
