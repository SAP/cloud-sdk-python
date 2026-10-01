"""Check that a project version increases according to PEP 440."""

import argparse
import sys

from packaging.version import InvalidVersion, Version


def check_version_bump(base: str, head: str) -> str:
    """Require the head version to be newer than the base version."""
    try:
        base_version = Version(base)
        head_version = Version(head)
    except InvalidVersion as error:
        raise ValueError(f"Cannot compare project versions: {error}") from error

    if head_version == base_version:
        raise ValueError(f"Version was not bumped (still {head_version}).")

    if head_version < base_version:
        raise ValueError(
            f"Version regression detected. Base is {base_version} but PR has "
            f"{head_version}."
        )

    return f"Version bump OK: {base_version} -> {head_version}"


def main() -> int:
    """Run the version comparison CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="Version on the pull request base commit")
    parser.add_argument("head", help="Version on the pull request head commit")
    args = parser.parse_args()

    try:
        message = check_version_bump(args.base, args.head)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
