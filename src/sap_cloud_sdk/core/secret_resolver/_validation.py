"""Shared input validation for secret resolution.

Lives in its own module so every resolver entry point can import the same
validators without risking an import cycle.
"""

from __future__ import annotations

import os
from pathlib import Path


def _validate_inputs(module: str, instance: str) -> None:
    """Single validation entry point: empty-check + component rules for both inputs."""
    if not isinstance(module, str) or not module.strip():
        raise ValueError("module name cannot be empty")
    if not isinstance(instance, str) or not instance.strip():
        raise ValueError("instance name cannot be empty")
    _validate_path_component("module", module)
    _validate_path_component("instance", instance)


def _validate_path_component(name: str, value: str) -> None:
    """Reject any value that is not a single safe filesystem path component.

    Called automatically before any path assembly or environment-variable
    fallback — a rejected value reads no files.
    Allows hyphens and internal dots (e.g. "hana-agent-memory", "aicore-instance",
    "my-tenant-us10"); rejects separators, absolute/UNC forms, '.'/'..', NUL,
    control characters, and values exceeding 255 characters.
    """
    if "\x00" in value:
        raise ValueError(f"{name} must not contain null bytes")
    if any(ord(c) < 32 for c in value):
        raise ValueError(f"{name} must not contain control characters")
    if len(value) > 255:
        raise ValueError(f"{name} exceeds maximum identifier length (255 chars)")
    if os.path.isabs(value):
        raise ValueError(f"{name} must not be an absolute path")
    if value.startswith("\\\\"):
        raise ValueError(f"{name} must not be a UNC path")
    # Normalise both separator styles; require exactly one non-traversal segment.
    parts = [p for p in value.replace("\\", "/").split("/") if p]
    if len(parts) != 1 or parts[0] in (".", ".."):
        raise ValueError(
            f"{name} must be a single path component "
            f"(no path separators, drive letters, or '.'/'..' segments); got {value!r}"
        )


def _assert_within_base(base_volume_mount: str, candidate: str) -> None:
    """Defense-in-depth: verify candidate resolves canonically inside base.

    Resolves symlinks on both sides. Silent when the path does not exist yet —
    the subsequent path-existence check surfaces a clean error in that case.
    Protects against TOCTOU / symlink-escape scenarios that pass component
    validation but point outside the trusted volume root at open-time.
    """
    try:
        base_real = Path(base_volume_mount).resolve(strict=True)
        cand_real = Path(candidate).resolve(strict=True)
    except (FileNotFoundError, OSError):
        return
    if cand_real != base_real and not cand_real.is_relative_to(base_real):
        raise ValueError(
            f"resolved binding path escapes trusted root {base_volume_mount!r}: "
            f"{candidate!r} → {cand_real}"
        )
