"""Tests for CI release-version scripts."""

from pathlib import Path
import subprocess
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).parents[2]
SCRIPTS = REPOSITORY_ROOT / ".github" / "scripts"


@pytest.mark.parametrize(
    ("version", "tag", "prerelease"),
    [
        ("1.0.0rc1", "v1.0.0rc1", "true"),
        ("1.0.0", "v1.0.0", "false"),
    ],
)
def test_validate_release_accepts_matching_metadata(
    version: str, tag: str, prerelease: str
):
    result = subprocess.run(
        [sys.executable, SCRIPTS / "validate_release.py", version, tag, prerelease],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("version", "tag", "prerelease"),
    [
        ("1.0.0rc1", "v1.0.0rc1", "false"),
        ("1.0.0-rc.1", "v1.0.0-rc.1", "true"),
        ("1.0.0", "v1.0.1", "false"),
    ],
)
def test_validate_release_rejects_mismatched_metadata(
    version: str, tag: str, prerelease: str
):
    result = subprocess.run(
        [sys.executable, SCRIPTS / "validate_release.py", version, tag, prerelease],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "ERROR:" in result.stderr


@pytest.mark.parametrize(
    ("base", "head"),
    [
        ("0.49.1", "1.0.0rc1"),
        ("1.0.0rc1", "1.0.0rc2"),
        ("1.0.0rc2", "1.0.0"),
    ],
)
def test_check_version_bump_accepts_newer_versions(base: str, head: str):
    result = subprocess.run(
        [sys.executable, SCRIPTS / "check_version_bump.py", base, head],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("base", "head"),
    [("1.0.0", "1.0.0rc1"), ("1.0.0", "1.0.0")],
)
def test_check_version_bump_rejects_non_increasing_versions(base: str, head: str):
    result = subprocess.run(
        [sys.executable, SCRIPTS / "check_version_bump.py", base, head],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "ERROR:" in result.stderr
