"""Environment-variable configuration for SAP AI Core content filtering.

Loads ``AICORE_FILTER_*`` runtime toggles into a :class:`ContentFiltering`
instance via :func:`load_from_env`.

Unlike :mod:`sap_cloud_sdk.core.secret_resolver` (mount-with-env-fallback for
service-binding credentials), this module reads only environment variables.
The settings here are runtime feature toggles (booleans, severity ints,
direction lists) with defaults, not credentials — so they don't live in
service bindings and don't need a mount layout.

Reads:

- ``AICORE_FILTER_ENABLED``       (bool, default ``true``)
- ``AICORE_FILTER_DIRECTIONS``    (comma list, default ``"input,output"``)
- ``AICORE_FILTER_HATE``          (int 0/2/4/6, default ``4``)
- ``AICORE_FILTER_VIOLENCE``      (int 0/2/4/6, default ``4``)
- ``AICORE_FILTER_SEXUAL``        (int 0/2/4/6, default ``4``)
- ``AICORE_FILTER_SELF_HARM``     (int 0/2/4/6, default ``4``)
- ``AICORE_FILTER_PROMPT_SHIELD`` (bool, default ``true``) — input-only
"""

from __future__ import annotations

import os

from ._models import (
    AzureContentFilter,
    ContentFiltering,
    InputFiltering,
    OutputFiltering,
    Severity,
)

_TRUTHY = frozenset({"true", "1", "yes"})

_VALID_SEVERITIES: set[int] = {s.value for s in Severity}


def _read_env_str(key: str, default: str = "") -> str:
    """Read a string env var. Trims whitespace. Returns ``default`` if absent."""
    raw = os.environ.get(key)
    return raw.strip() if raw is not None else default


def _read_env_bool(key: str, default: bool = False) -> bool:
    """Read a boolean env var.

    ``true``/``1``/``yes`` (case-insensitive) are True; anything else is False.
    Returns ``default`` if the variable is absent.
    """
    raw = os.environ.get(key)
    return (raw.strip().lower() in _TRUTHY) if raw is not None else default


def _read_env_choice(key: str, choices: set[int], default: int) -> int:
    """Read an int env var, validate membership in ``choices``.

    Returns ``default`` when the variable is absent. Raises ``ValueError`` if
    the value cannot be parsed as ``int`` or is not in ``choices``.
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
    return value


def load_from_env() -> ContentFiltering | None:
    """Build a :class:`ContentFiltering` from ``AICORE_FILTER_*`` env vars.

    Returns ``None`` when ``AICORE_FILTER_ENABLED=false``, disabling
    filtering entirely. Constructs a single :class:`AzureContentFilter` per
    enabled direction (LlamaGuard is opt-in via explicit programmatic config).
    """
    if not _read_env_bool("AICORE_FILTER_ENABLED", default=True):
        return None

    directions_raw = _read_env_str("AICORE_FILTER_DIRECTIONS", "input,output")
    directions = {d.strip() for d in directions_raw.split(",") if d.strip()}

    hate = Severity(_read_env_choice("AICORE_FILTER_HATE", _VALID_SEVERITIES, default=4))
    violence = Severity(
        _read_env_choice("AICORE_FILTER_VIOLENCE", _VALID_SEVERITIES, default=4)
    )
    sexual = Severity(
        _read_env_choice("AICORE_FILTER_SEXUAL", _VALID_SEVERITIES, default=4)
    )
    self_harm = Severity(
        _read_env_choice("AICORE_FILTER_SELF_HARM", _VALID_SEVERITIES, default=4)
    )
    prompt_shield = _read_env_bool("AICORE_FILTER_PROMPT_SHIELD", default=True)

    input_filtering: InputFiltering | None = None
    if "input" in directions:
        input_filtering = InputFiltering(
            filters=[
                AzureContentFilter(
                    hate=hate,
                    violence=violence,
                    sexual=sexual,
                    self_harm=self_harm,
                    prompt_shield=prompt_shield,
                )
            ]
        )

    output_filtering: OutputFiltering | None = None
    if "output" in directions:
        output_filtering = OutputFiltering(
            filters=[
                AzureContentFilter(
                    hate=hate,
                    violence=violence,
                    sexual=sexual,
                    self_harm=self_harm,
                )
            ]
        )

    return ContentFiltering(
        input_filtering=input_filtering,
        output_filtering=output_filtering,
    )
