"""Typed environment-variable readers for runtime toggles.

Distinct from :mod:`sap_cloud_sdk.core.secret_resolver`, which loads
credentials from mounted volumes with env-var fallback. This module is for
non-credential runtime toggles (feature flags, thresholds, directions) that
have defaults and don't live in service bindings.
"""

from __future__ import annotations

import os
from typing import TypeVar

T = TypeVar("T", bound=int)

_TRUTHY = frozenset({"true", "1", "yes"})


def read_env_str(key: str, default: str = "") -> str:
    """Read a string env var. Trims whitespace. Returns ``default`` if absent."""
    raw = os.environ.get(key)
    return raw.strip() if raw is not None else default


def read_env_bool(key: str, default: bool = False) -> bool:
    """Read a boolean env var.

    ``true``/``1``/``yes`` (case-insensitive) are True; anything else is False.
    Returns ``default`` if the variable is absent.
    """
    raw = os.environ.get(key)
    return (raw.strip().lower() in _TRUTHY) if raw is not None else default


def read_env_choice(key: str, choices: set[T], default: T) -> T:
    """Read an int env var, validate membership in ``choices``.

    Returns ``default`` when the variable is absent. Raises ``ValueError`` if
    the value cannot be parsed as ``int`` or is not in ``choices``.

    Used for severity thresholds: ``read_env_choice('AICORE_FILTER_HATE',
    {0, 2, 4, 6}, default=4)``. The ``T`` type variable is bound to ``int``
    so callers can pass ``set[Severity]`` (an ``IntEnum`` subclass) and get
    the matching enum value back; ``T`` also accepts plain ``int``.
    """
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError as e:
        raise ValueError(f"{key} must be one of {sorted(choices)}, got {raw!r}") from e
    if value not in choices:
        raise ValueError(f"{key} must be one of {sorted(choices)}, got {value}")
    return value  # type: ignore[return-value]
