"""Validate a PEP 440 version string passed via VERSION_INPUT env var."""

import os
import sys

from packaging.version import InvalidVersion, Version


def main() -> int:
    version_input = os.environ.get("VERSION_INPUT", "")
    try:
        Version(version_input)
    except InvalidVersion as e:
        print(f"ERROR: Invalid version '{version_input}': {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
