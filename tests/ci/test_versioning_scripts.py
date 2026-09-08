"""Tests for CI release-version scripts."""

from pathlib import Path
import subprocess
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).parents[2]
SCRIPTS = REPOSITORY_ROOT / ".github" / "scripts"


@pytest.mark.parametrize(
    ("version", "prerelease"),
    [
        ("1.0.0rc1", "true"),
        ("1.0.0", "false"),
    ],
)
def test_validate_prerelease_accepts_matching_status(
    version: str, prerelease: str
):
    result = subprocess.run(
        [sys.executable, SCRIPTS / "validate_prerelease.py", version, prerelease],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("version", "prerelease"),
    [
        ("1.0.0rc1", "false"),
        ("1.0.0", "true"),
    ],
)
def test_validate_prerelease_rejects_mismatched_status(
    version: str, prerelease: str
):
    result = subprocess.run(
        [sys.executable, SCRIPTS / "validate_prerelease.py", version, prerelease],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "ERROR:" in result.stderr


def test_validate_prerelease_rejects_invalid_version():
    result = subprocess.run(
        [sys.executable, SCRIPTS / "validate_prerelease.py", "invalid", "false"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    assert "not a valid PEP 440 version" in result.stderr


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
