"""Allowlist validation and safe encoding for destination resource name path segments."""

from __future__ import annotations

import re
from urllib.parse import quote

# Allowlist grammar for destination, fragment, and certificate resource names.
#
# First character must be alphanumeric — this prevents the entire segment from
# ever being "." or ".." (dot-only segments), which are path traversal primitives
# that urllib.parse.quote() would leave untouched.
#
# The tail allows letters, digits, dot, underscore, and hyphen — the character
# set used by real SAP Destination Service names in production.
#
# The 200-character cap covers all known production names with margin. Encoding
# is applied to the *base* name only (any @level suffix is stripped by the client
# layer before this helper is called), so the cap applies to the base name alone.
#
# Characters explicitly excluded and why:
#   @  — V2 level-hint separator; handled at the client layer, not here
#   /  — path separator
#   \  — path separator (Windows)
#   ?  — query string start
#   #  — fragment start
#   %  — percent-encoding that could hide the above
#   <space>, \x00, and other control chars — protocol delimiters / NUL
#   Non-ASCII Unicode — outside the Destination Service name contract
_NAME_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._\-]{0,199}"
_RESOURCE_NAME_RE = re.compile(_NAME_PATTERN)


def validate_resource_name(name: str) -> str:
    """Return *name* unchanged, or raise :exc:`ValueError` if it is not a safe identifier.

    A safe identifier matches ``[A-Za-z0-9][A-Za-z0-9._-]{0,199}``:

    * First character alphanumeric — prevents "." and ".." path traversal segments.
    * Tail: letters, digits, dot, underscore, hyphen only.
    * Maximum 200 characters (base name, before any ``@level`` suffix).

    Args:
        name: The resource name to validate.

    Returns:
        The name unchanged (for convenient inline use).

    Raises:
        ValueError: If *name* does not match the allowlist grammar.
    """
    if not isinstance(name, str) or not _RESOURCE_NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid resource name {name!r}: must match {_NAME_PATTERN}")
    return name


def encode_path_segment(name: str) -> str:
    """Validate *name* and return it percent-encoded for safe URL path interpolation.

    For every character in the allowlist grammar, :func:`urllib.parse.quote` with
    ``safe=""`` is an identity transform (all allowed characters are in urllib's
    always-safe set).  The encoding layer is kept as defense-in-depth: if the
    grammar is ever widened to include a character that is not always-safe, the
    encoding will catch it before it reaches the wire.

    Args:
        name: The resource name to validate and encode.

    Returns:
        The percent-encoded name string.

    Raises:
        ValueError: If *name* does not pass :func:`validate_resource_name`.
    """
    return quote(validate_resource_name(name), safe="")
