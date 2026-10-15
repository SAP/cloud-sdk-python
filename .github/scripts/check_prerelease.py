"""Print 'true' if VERSION env var is a pre-release, 'false' otherwise."""

import os
import sys

from packaging.version import InvalidVersion, Version


def main() -> int:
    version = os.environ.get("VERSION", "")
    try:
        print("true" if Version(version).is_prerelease else "false")
    except InvalidVersion as e:
        print(f"ERROR: Invalid version '{version}': {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
