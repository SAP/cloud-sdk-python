# Security Handler User Guide

This module provides a composable pre-LLM security gate for agent pipelines. It covers
input sanitization, prompt injection detection, and pluggable guardrail enforcement.

## Import

```python
from sap_cloud_sdk.security_handler import (
    SecurityHandler,
    SecurityConfig,
    ScanResult,
    Violation,
    Severity,
    ViolationType,
    Guardrail,
    ForbiddenPatternGuardrail,
    InjectionDetector,
    PatternRule,
    InputTooLongError,
    escape_xml_tags,
)
```

## Quick Start

### Basic usage

```python
from sap_cloud_sdk.security_handler import SecurityHandler

handler = SecurityHandler()
result = handler.scan(user_input)

if result.is_blocked:
    raise ValueError(result.violations[0].description)

# result.sanitized_text is safe to embed in a prompt
process(result.sanitized_text)
```

### Custom configuration

```python
from sap_cloud_sdk.security_handler import SecurityHandler, SecurityConfig, Severity

handler = SecurityHandler(SecurityConfig(
    min_blocking_severity=Severity.HIGH,
    custom_forbidden_patterns=[r"competitor_name", r"internal_project_codename"],
))
```

## What `scan()` does

`scan()` runs three steps in order:

1. **Sanitize** — strips control characters, normalises whitespace, enforces max length.
2. **Injection detection** — matches against built-in prompt injection patterns (instruction
   overrides, persona redefinition, jailbreak keywords, templating tokens, etc.).
3. **Guardrails** — runs any custom forbidden-pattern or user-defined guardrail rules.

It always returns a `ScanResult`. It never raises unless input exceeds `max_input_length`.

## ScanResult

```python
result.original_text    # the raw input as received
result.sanitized_text   # cleaned input, safe to use in prompts
result.violations       # list of Violation objects (may be empty)
result.is_blocked       # True if any violation meets min_blocking_severity
result.is_clean         # True if no violations at all
result.highest_severity # the worst Severity found, or None
```

## Severity levels

| Level | When used |
|---|---|
| `LOW` | Minor style issues (response prefix injection) |
| `MEDIUM` | Templating tokens, control characters, context redefinition |
| `HIGH` | Jailbreak keywords, persona redefinition, system prompt extraction |
| `CRITICAL` | Direct instruction override attempts |

Default blocking threshold is `MEDIUM` — anything `MEDIUM` or above sets `is_blocked=True`.

## SecurityConfig options

| Field | Default | Description |
|---|---|---|
| `max_input_length` | `10_000` | Hard length cap. Inputs over this are blocked immediately. |
| `min_blocking_severity` | `MEDIUM` | Minimum severity that sets `is_blocked=True`. |
| `injection_detection` | `True` | Enable/disable built-in injection detector. |
| `templating_token_detection` | `True` | Enable/disable `${...}`, `{{...}}`, `<<...>>` checks. |
| `custom_forbidden_patterns` | `[]` | Extra case-insensitive regex patterns to block. |
| `extra_injection_rules` | `[]` | Additional `PatternRule` instances for injection detection. |
| `custom_guardrails` | `[]` | Fully custom `Guardrail` implementations. |

## Custom guardrails

Extend `Guardrail` to add domain-specific rules:

```python
from sap_cloud_sdk.security_handler import Guardrail, Violation, Severity, ViolationType

class NoPhoneNumberGuardrail(Guardrail):
    def check(self, text: str) -> list[Violation]:
        import re
        if re.search(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b", text):
            return [Violation(
                type=ViolationType.FORBIDDEN_PATTERN,
                severity=Severity.HIGH,
                description="Phone number detected in input",
            )]
        return []

handler = SecurityHandler(SecurityConfig(
    custom_guardrails=[NoPhoneNumberGuardrail()],
))
```

## XML tag escaping

Use `escape_xml_tags()` when embedding user input inside sentinel-wrapped prompt templates
to prevent tag-breakout attacks:

```python
from sap_cloud_sdk.security_handler import escape_xml_tags

prompt = f"<user_query>{escape_xml_tags(result.sanitized_text)}</user_query>"
```

## Error handling

```python
from sap_cloud_sdk.security_handler import InputTooLongError

try:
    result = handler.scan(very_long_text)
except InputTooLongError as e:
    print(f"Input too long: {e.length} chars (max {e.max_length})")
```

## Adding custom injection rules

```python
from sap_cloud_sdk.security_handler import SecurityConfig, SecurityHandler, PatternRule, Severity

handler = SecurityHandler(SecurityConfig(
    extra_injection_rules=[
        PatternRule(
            pattern=r"execute\s+as\s+admin",
            severity=Severity.CRITICAL,
            description="Admin execution attempt",
        ),
    ]
))
```
