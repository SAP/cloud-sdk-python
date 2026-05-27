from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    INJECTION_ATTEMPT = "injection_attempt"
    TEMPLATING_TOKEN = "templating_token"
    INPUT_TOO_LONG = "input_too_long"
    FORBIDDEN_PATTERN = "forbidden_pattern"
    CONTROL_CHARACTER = "control_character"


@dataclass
class Violation:
    type: ViolationType
    severity: Severity
    description: str
    matched_text: Optional[str] = None


@dataclass
class ScanResult:
    original_text: str
    sanitized_text: str
    violations: list[Violation] = field(default_factory=list)
    is_blocked: bool = False

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0

    @property
    def highest_severity(self) -> Optional[Severity]:
        if not self.violations:
            return None
        order = {
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }
        return max(self.violations, key=lambda v: order[v.severity]).severity
