"""Validate package metadata against a GitHub Release."""

import argparse
import sys

from packaging.version import InvalidVersion, Version


def validate_release(
    raw_version: str, release_tag: str, release_is_prerelease: bool
) -> str:
    """Validate version normalization, tag, and pre-release status."""
    try:
        version = Version(raw_version)
    except InvalidVersion as error:
        raise ValueError(
            f"'{raw_version}' is not a valid PEP 440 version."
        ) from error

    normalized_version = str(version)
    if raw_version != normalized_version:
        raise ValueError(
            f"Version '{raw_version}' is not in its normalized PEP 440 form. "
            f"Use '{normalized_version}' instead."
        )

    expected_tag = f"v{normalized_version}"
    if release_tag != expected_tag:
        raise ValueError(
            f"GitHub Release tag '{release_tag}' does not match pyproject.toml "
            f"version '{raw_version}'. Expected '{expected_tag}'."
        )

    if version.is_prerelease != release_is_prerelease:
        expected_setting = "enabled" if version.is_prerelease else "disabled"
        raise ValueError(
            "The GitHub Release pre-release setting does not match version "
            f"'{raw_version}'. Set pre-release to {expected_setting}, then rerun "
            "this workflow."
        )

    return (
        f"Release metadata is valid: tag={release_tag}, "
        f"pre-release={str(release_is_prerelease).lower()}"
    )


def main() -> int:
    """Run the release validation CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Package version from pyproject.toml")
    parser.add_argument("tag", help="GitHub Release tag")
    parser.add_argument(
        "prerelease",
        choices=("true", "false"),
        help="Current GitHub Release pre-release setting",
    )
    args = parser.parse_args()

    try:
        message = validate_release(
            args.version, args.tag, args.prerelease == "true"
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
