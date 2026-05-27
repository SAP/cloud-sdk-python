"""Input sanitizer — pre-LLM programmatic filter.

Adapted from the procurement-ai-service InputSanitizer pattern.
Applies to user input ONLY — never to agent output, system prompts, or API data.

Protections:
  - Control character stripping (preserves \\n, \\r, \\t)
  - Horizontal whitespace normalization (preserves newlines)
  - Max length enforcement with rejection (never silent truncation)
  - XML tag escaping for sentinel-wrapped prompt injection prevention
"""

import logging
import re

from .models import Severity, Violation, ViolationType

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = (
    10_000  # ~1,700 words — generous for chat; prevents resource exhaustion
)

# Unicode Cc (control) characters, EXCEPT \n (0x0A), \r (0x0D), \t (0x09).
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


class InputTooLongError(ValueError):
    """Raised when user input exceeds the configured maximum length."""

    def __init__(self, length: int, max_length: int) -> None:
        self.length = length
        self.max_length = max_length
        super().__init__(
            f"Input length ({length:,} chars) exceeds maximum ({max_length:,} chars). "
            "Please shorten your message and try again."
        )


def escape_xml_tags(text: str) -> str:
    """Escape XML-significant characters before embedding user text in sentinel tags.

    Prevents tag-breakout attacks where user input contains closing tags like
    </user_query>. Apply at interpolation points, not as a general sanitizer.
    """
    if not text:
        return text
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sanitize(
    text: str | None,
    max_length: int = MAX_INPUT_LENGTH,
) -> tuple[str | None, list[Violation]]:
    """Sanitize raw user input before passing to any LLM or agent node.

    Returns (cleaned_text, violations). Raises InputTooLongError if the
    cleaned text exceeds max_length — reject, never silently truncate.
    """
    if not text:
        return text, []

    violations: list[Violation] = []

    # 1. Strip control characters (keep \n, \r, \t)
    cleaned = _CONTROL_CHAR_RE.sub("", text)
    if cleaned != text:
        violations.append(
            Violation(
                type=ViolationType.CONTROL_CHARACTER,
                severity=Severity.MEDIUM,
                description="Control characters stripped from input",
            )
        )

    # 2. Normalize horizontal whitespace — collapse runs of space/NBSP to a
    #    single space, preserving newlines and tabs verbatim.
    result: list[str] = []
    in_space_run = False
    for ch in cleaned:
        if ch in (" ", "\xa0"):
            if not in_space_run:
                result.append(" ")
                in_space_run = True
        else:
            result.append(ch)
            in_space_run = False
    cleaned = "".join(result)

    # 3. Trim leading/trailing whitespace
    cleaned = cleaned.strip()

    # 4. Enforce max length — reject, don't silently truncate
    if len(cleaned) > max_length:
        logger.warning(
            "sanitize: input too long (%d chars, max %d)", len(cleaned), max_length
        )
        raise InputTooLongError(len(cleaned), max_length)

    return cleaned, violations
