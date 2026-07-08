"""Utilities for mapping dataclass fields to secret store keys."""

from typing import Any, Dict, Tuple
from dataclasses import fields, is_dataclass


def _get_field_map(target: Any) -> Dict[str, Tuple[str, type]]:
    """
    Build a mapping from secret key -> (attribute_name, attribute_type) for a dataclass instance.

    Priority:
      1. Use field.metadata["secret"] if present as the key
      2. Fallback to the lowercase dataclass field name
    Only string-typed fields are supported.
    """
    if not is_dataclass(target) or isinstance(target, type):
        raise TypeError("target must be a dataclass instance")

    mapping: Dict[str, Tuple[str, type]] = {}
    for f in fields(target):
        # Only support string fields for secrets (consistent with Go SDK)
        # Allow plain 'str' annotations; reject others to keep behavior predictable
        if f.type is not str:
            raise TypeError(
                f"target field '{f.name}' is not a string (only str fields are supported)"
            )
        key = f.metadata.get("secret") if hasattr(f, "metadata") else None
        if key and isinstance(key, str) and key.strip():
            mapping[key] = (f.name, f.type)
        else:
            mapping[f.name.lower()] = (f.name, f.type)
    return mapping
