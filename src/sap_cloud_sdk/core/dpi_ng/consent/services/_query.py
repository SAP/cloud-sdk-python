"""Shared OData query helper used by all consent service clients."""

from __future__ import annotations

from typing import Any


def _apply_query(q: Any, params: dict[str, Any]) -> Any:
    """Apply supported OData query options to a Query builder and return it.

    Supported keys: ``filter``, ``top``, ``skip``, ``orderby``.
    Unknown keys are silently ignored.

    Args:
        q: A python-odata ``Query`` instance to apply options to.
        params: Mapping of OData option names to their values.

    Returns:
        The Query instance with all supported options applied.
    """
    if "filter" in params:
        q = q.raw({"$filter": params["filter"]})
    if "top" in params:
        q = q.limit(int(params["top"]))
    if "skip" in params:
        q = q.offset(int(params["skip"]))
    if "orderby" in params:
        q = q.raw({"$orderby": params["orderby"]})
    return q
