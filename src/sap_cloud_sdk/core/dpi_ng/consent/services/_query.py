"""Shared OData query helper used by all consent service clients."""

from __future__ import annotations

from typing import Any


def _apply_query(q: Any, params: dict[str, Any]) -> Any:
    """Apply OData query options (filter, top, skip, orderby) to a Query builder."""
    if "filter" in params:
        q = q.raw({"$filter": params["filter"]})
    if "top" in params:
        q = q.limit(int(params["top"]))
    if "skip" in params:
        q = q.offset(int(params["skip"]))
    if "orderby" in params:
        q = q.raw({"$orderby": params["orderby"]})
    return q
