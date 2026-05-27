"""Unit tests for data models — Severity, ViolationType, Violation, ScanResult."""

import pytest

from sap_cloud_sdk.security_handler.models import (
    ScanResult,
    Severity,
    Violation,
    ViolationType,
)


class TestSeverity:

    def test_severity_values(self):
        assert Severity.LOW == "low"
        assert Severity.MEDIUM == "medium"
        assert Severity.HIGH == "high"
        assert Severity.CRITICAL == "critical"


class TestViolation:

    def test_violation_fields(self):
        v = Violation(
            type=ViolationType.INJECTION_ATTEMPT,
            severity=Severity.HIGH,
            description="Instruction override attempt",
            matched_text="ignore previous instructions",
        )
        assert v.type == ViolationType.INJECTION_ATTEMPT
        assert v.severity == Severity.HIGH
        assert v.matched_text == "ignore previous instructions"

    def test_matched_text_defaults_to_none(self):
        v = Violation(
            type=ViolationType.CONTROL_CHARACTER,
            severity=Severity.MEDIUM,
            description="Control chars stripped",
        )
        assert v.matched_text is None


class TestScanResult:

    def test_is_clean_true_when_no_violations(self):
        result = ScanResult(original_text="hello", sanitized_text="hello")
        assert result.is_clean is True
        assert result.is_blocked is False

    def test_is_clean_false_when_violations_present(self):
        v = Violation(ViolationType.INJECTION_ATTEMPT, Severity.HIGH, "desc")
        result = ScanResult(
            original_text="bad input",
            sanitized_text="bad input",
            violations=[v],
        )
        assert result.is_clean is False

    def test_highest_severity_none_when_no_violations(self):
        result = ScanResult(original_text="ok", sanitized_text="ok")
        assert result.highest_severity is None

    def test_highest_severity_returns_worst(self):
        violations = [
            Violation(ViolationType.CONTROL_CHARACTER, Severity.LOW, "low"),
            Violation(ViolationType.INJECTION_ATTEMPT, Severity.CRITICAL, "critical"),
            Violation(ViolationType.FORBIDDEN_PATTERN, Severity.HIGH, "high"),
        ]
        result = ScanResult(
            original_text="x", sanitized_text="x", violations=violations
        )
        assert result.highest_severity == Severity.CRITICAL
