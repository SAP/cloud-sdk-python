"""Validate that a package version matches the GitHub pre-release setting."""

import argparse
import sys

from packaging.version import InvalidVersion, Version


def validate_prerelease(raw_version: str, release_is_prerelease: bool) -> str:
    """Require the package and GitHub Release to agree on pre-release status."""
    try:
        version = Version(raw_version)
    except InvalidVersion as error:
        raise ValueError(
            f"'{raw_version}' is not a valid PEP 440 version."
        ) from error

    if version.is_prerelease != release_is_prerelease:
        expected_setting = "enabled" if version.is_prerelease else "disabled"
        raise ValueError(
            "The GitHub Release pre-release setting does not match version "
            f"'{raw_version}'. Set pre-release to {expected_setting} and publish "
            "a new release event."
        )

    return (
        f"Pre-release status is valid: version={raw_version}, "
        f"pre-release={str(release_is_prerelease).lower()}"
    )


def main() -> int:
    """Run the pre-release validation CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Package version from pyproject.toml")
    parser.add_argument(
        "prerelease",
        choices=("true", "false"),
        help="GitHub Release pre-release setting",
    )
    args = parser.parse_args()

    try:
        message = validate_prerelease(
            args.version, args.prerelease == "true"
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
