"""Fixture module with ``from __future__ import annotations`` active.

``from __future__ import annotations`` turns all annotations in THIS module into
strings at runtime.  Importing the dataclass defined here lets tests verify that
``_get_field_map()`` uses ``typing.get_type_hints()`` (which resolves string
annotations) rather than ``f.type`` directly (which would return a string and
break Optional[str] detection).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PEP563Config:
    """Dataclass whose annotations are stored as strings due to PEP 563.

    At runtime (without get_type_hints):
        PEP563Config.__annotations__ == {"required": "str", "optional": "Optional[str]"}

    After get_type_hints():
        {"required": str, "optional": typing.Optional[str]}
    """

    required: str = ""
    optional: Optional[str] = None
