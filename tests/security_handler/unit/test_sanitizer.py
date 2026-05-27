"""Unit tests for the input sanitizer."""

import pytest

from sap_cloud_sdk.security_handler.models import Severity, ViolationType
from sap_cloud_sdk.security_handler.sanitizer import (
    InputTooLongError,
    MAX_INPUT_LENGTH,
    escape_xml_tags,
    sanitize,
)


class TestSanitize:

    def test_clean_input_passes_through(self):
        cleaned, violations = sanitize("Hello, world!")
        assert cleaned == "Hello, world!"
        assert violations == []

    def test_none_input_returns_none(self):
        cleaned, violations = sanitize(None)
        assert cleaned is None
        assert violations == []

    def test_empty_string_returns_empty(self):
        cleaned, violations = sanitize("")
        assert cleaned == ""
        assert violations == []

    def test_strips_control_characters(self):
        # \x00 is a null byte — a control character
        cleaned, violations = sanitize("hello\x00world")
        assert cleaned == "helloworld"
        assert len(violations) == 1
        assert violations[0].type == ViolationType.CONTROL_CHARACTER
        assert violations[0].severity == Severity.MEDIUM

    def test_preserves_newlines_and_tabs(self):
        # \n, \r, \t are allowed control characters
        cleaned, violations = sanitize("line1\nline2\ttabbed")
        assert cleaned == "line1\nline2\ttabbed"
        assert violations == []

    def test_collapses_multiple_spaces(self):
        cleaned, violations = sanitize("too   many    spaces")
        assert cleaned == "too many spaces"
        assert violations == []

    def test_strips_leading_trailing_whitespace(self):
        cleaned, violations = sanitize("  trimmed  ")
        assert cleaned == "trimmed"

    def test_raises_input_too_long_error(self):
        long_input = "a" * (MAX_INPUT_LENGTH + 1)
        with pytest.raises(InputTooLongError) as exc_info:
            sanitize(long_input)
        assert exc_info.value.length == MAX_INPUT_LENGTH + 1
        assert exc_info.value.max_length == MAX_INPUT_LENGTH

    def test_custom_max_length(self):
        with pytest.raises(InputTooLongError):
            sanitize("hello world", max_length=5)

    def test_exactly_at_max_length_is_allowed(self):
        text = "a" * MAX_INPUT_LENGTH
        cleaned, violations = sanitize(text)
        assert cleaned is not None
        assert len(cleaned) == MAX_INPUT_LENGTH


class TestEscapeXmlTags:

    def test_escapes_angle_brackets(self):
        assert escape_xml_tags("<script>") == "&lt;script&gt;"

    def test_escapes_ampersand(self):
        assert escape_xml_tags("a & b") == "a &amp; b"

    def test_clean_text_unchanged(self):
        assert escape_xml_tags("hello world") == "hello world"

    def test_empty_string(self):
        assert escape_xml_tags("") == ""
