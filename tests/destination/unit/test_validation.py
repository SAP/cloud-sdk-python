"""Unit tests for destination resource name validation helpers."""

import pytest

from sap_cloud_sdk.destination.utils._validation import (
    encode_path_segment,
    validate_resource_name,
)


class TestValidateResourceName:

    # --- Valid names (must be accepted unchanged) ---

    @pytest.mark.parametrize(
        "name",
        [
            "MyDest",
            "my-dest",
            "dest.v2",
            "dest_v2",
            "a",
            "A",
            "Z0",
            "AuditLogV3_Destination",
            "sap-managed-runtime-ias-exttest-dev-eu12",
            "cctr-monitor-s4-dest",
            "SCMCore-CC3-Support",
            "a" * 200,  # boundary: 200 chars
        ],
    )
    def test_accepts_valid_names(self, name: str):
        assert validate_resource_name(name) == name

    # --- Invalid names (must raise ValueError) ---

    @pytest.mark.parametrize(
        "name",
        [
            ".",
            "..",
            "../etc/passwd",
            "/root",
            "a/b",
            "a\\b",
            "a@b",
            "a?query=1",
            "a#fragment",
            "a%2Fb",        # percent-encoded slash
            "a%2e%2e",      # percent-encoded dot-dot
            "a b",          # whitespace
            "a\x00b",       # NUL byte
            "café",         # Unicode outside ASCII
            "",             # empty
            "-leading",     # first char is hyphen
            ".leading",     # first char is dot
            "a" * 201,      # overlong: 201 chars
        ],
    )
    def test_rejects_invalid_names(self, name: str):
        with pytest.raises(ValueError):
            validate_resource_name(name)

    def test_rejects_non_string_input(self):
        with pytest.raises(ValueError):
            validate_resource_name(None)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]

    def test_rejects_integer_input(self):
        with pytest.raises(ValueError):
            validate_resource_name(42)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]

    def test_error_message_includes_name(self):
        with pytest.raises(ValueError, match="Invalid resource name"):
            validate_resource_name("../evil")


class TestEncodePathSegment:

    @pytest.mark.parametrize(
        "name",
        [
            "MyDest",
            "my-dest",
            "dest.v2",
            "dest_v2",
            "a",
            "AuditLogV3_Destination",
            "sap-managed-runtime-ias-exttest-dev-eu12",
        ],
    )
    def test_valid_name_is_returned_unchanged(self, name: str):
        """For all chars in the allowlist, quote(safe='') must be identity."""
        assert encode_path_segment(name) == name

    def test_invalid_name_raises_value_error(self):
        with pytest.raises(ValueError):
            encode_path_segment("../evil")

    def test_at_sign_rejected(self):
        with pytest.raises(ValueError):
            encode_path_segment("a@b")
