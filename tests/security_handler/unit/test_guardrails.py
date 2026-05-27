"""Unit tests for security guardrails."""

import pytest

from sap_cloud_sdk.security_handler.guardrails import ForbiddenPatternGuardrail
from sap_cloud_sdk.security_handler.models import Severity, ViolationType


class TestForbiddenPatternGuardrail:

    def test_clean_input_returns_no_violations(self):
        guardrail = ForbiddenPatternGuardrail(patterns=[r"badword"])
        assert guardrail.check("hello world") == []

    def test_detects_forbidden_pattern(self):
        guardrail = ForbiddenPatternGuardrail(patterns=[r"competitor_name"])
        violations = guardrail.check("use competitor_name instead")
        assert len(violations) == 1
        assert violations[0].type == ViolationType.FORBIDDEN_PATTERN

    def test_match_is_case_insensitive(self):
        guardrail = ForbiddenPatternGuardrail(patterns=[r"badword"])
        violations = guardrail.check("BADWORD found here")
        assert len(violations) == 1

    def test_default_severity_is_high(self):
        guardrail = ForbiddenPatternGuardrail(patterns=[r"forbidden"])
        violations = guardrail.check("this is forbidden")
        assert violations[0].severity == Severity.HIGH

    def test_custom_severity(self):
        guardrail = ForbiddenPatternGuardrail(
            patterns=[r"warning_word"], severity=Severity.MEDIUM
        )
        violations = guardrail.check("contains warning_word here")
        assert violations[0].severity == Severity.MEDIUM

    def test_multiple_patterns_each_reported(self):
        guardrail = ForbiddenPatternGuardrail(patterns=[r"alpha", r"beta"])
        violations = guardrail.check("alpha and beta both present")
        assert len(violations) == 2

    def test_matched_text_is_populated(self):
        guardrail = ForbiddenPatternGuardrail(patterns=[r"secret\d+"])
        violations = guardrail.check("my code is secret42")
        assert violations[0].matched_text == "secret42"
