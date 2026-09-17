"""Shared serialization utilities for dpi_ng.consent DTOs."""

from __future__ import annotations

import re
from typing import Any

_RE = re.compile(r"_([a-z])")


def _to_camel(s: str) -> str:
    return _RE.sub(lambda m: m.group(1).upper(), s)


class _CamelSerializable:
    """Mixin that serialises snake_case dataclass fields to camelCase for OData action payloads."""

    def to_dict(self) -> dict[str, Any]:
        return {_to_camel(k): v for k, v in self.__dict__.items() if v is not None}
