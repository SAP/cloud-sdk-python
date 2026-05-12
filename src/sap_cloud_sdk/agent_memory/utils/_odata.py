"""OData v4 query-building utilities for the Agent Memory service.

When migrating to a non-OData API, replace the helpers in this file and update
the call sites in ``client.py``. The client method signatures stay the same.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class FilterDefinition:
    """A single ``contains`` predicate used in the ``filter`` parameter.

    Args:
        target: Field to filter on. Allowed values: ``"metadata"``, ``"content"``.
        contains: Required substring. Must be non-empty.
    """

    target: str
    contains: str


def _escape_odata_string(value: str) -> str:
    """Escape single quotes in an OData string literal ('' per OData 4.01)."""
    return value.replace("'", "''")


def build_contains_clauses(clauses: list[FilterDefinition]) -> list[str]:
    """Convert FilterDefinition objects into OData contains() expressions."""
    return [
        f"contains({clause.target}, '{_escape_odata_string(clause.contains)}')"
        for clause in clauses
    ]


def build_memory_filter(
    agent_id: Optional[str] = None,
    invoker_id: Optional[str] = None,
    filter_clauses: Optional[list[FilterDefinition]] = None,
) -> Optional[str]:
    """Build an OData ``$filter`` expression for memories.

    Args:
        agent_id: Filter by agent identifier.
        invoker_id: Filter by invoker/user identifier.
        filter_clauses: Additional ``contains`` predicates.

    Returns:
        A ``$filter`` string, or ``None`` if no filters are requested.
    """
    parts: list[str] = []
    if agent_id:
        parts.append(f"agentID eq '{_escape_odata_string(agent_id)}'")
    if invoker_id:
        parts.append(f"invokerID eq '{_escape_odata_string(invoker_id)}'")
    if filter_clauses:
        parts.extend(build_contains_clauses(filter_clauses))
    return " and ".join(parts) if parts else None


def build_message_filter(
    agent_id: Optional[str] = None,
    invoker_id: Optional[str] = None,
    message_group: Optional[str] = None,
    role: Optional[str] = None,
    filter_clauses: Optional[list[FilterDefinition]] = None,
) -> Optional[str]:
    """Build an OData ``$filter`` expression for messages.

    Args:
        agent_id: Filter by agent identifier.
        invoker_id: Filter by invoker/user identifier.
        message_group: Filter by message group.
        role: Filter by message role (USER, ASSISTANT, SYSTEM, TOOL).
        filter_clauses: Additional ``contains`` predicates.

    Returns:
        A ``$filter`` string, or ``None`` if no filters are requested.
    """
    parts: list[str] = []
    if agent_id:
        parts.append(f"agentID eq '{_escape_odata_string(agent_id)}'")
    if invoker_id:
        parts.append(f"invokerID eq '{_escape_odata_string(invoker_id)}'")
    if message_group:
        parts.append(f"messageGroup eq '{_escape_odata_string(message_group)}'")
    if role:
        parts.append(f"role eq '{_escape_odata_string(role)}'")
    if filter_clauses:
        parts.extend(build_contains_clauses(filter_clauses))
    return " and ".join(parts) if parts else None


def build_list_params(
    *,
    filter_expr: Optional[str] = None,
    search: Optional[str] = None,
    select: Optional[str] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
    order_by: Optional[str] = None,
    count: bool = False,
) -> dict[str, str]:
    """Build a dictionary of OData query parameters for list operations.

    Args:
        filter_expr: OData ``$filter`` expression string.
        search: Free-text search expression (``$search``).
        select: Comma-separated list of properties to return (``$select``).
        top: Maximum number of results (``$top``).
        skip: Number of results to skip for pagination (``$skip``).
        order_by: Sort field and direction, e.g. ``"createTimestamp desc"`` (``$orderby``).
        count: Whether to request the total count (``$count=true``).

    Returns:
        A dict of query parameter name → value strings.
    """
    params: dict[str, str] = {}
    if filter_expr:
        params["$filter"] = filter_expr
    if search:
        params["$search"] = search
    if select:
        # The server's audit log handler requires agentID and invokerID to be
        # present on every read. Ensure they are always included in $select to
        # avoid a 500 error from a NULL constraint on the access log table.
        required = {"agentID", "invokerID"}
        fields = {f.strip() for f in select.split(",")}
        fields |= required
        params["$select"] = ",".join(sorted(fields))
    if top is not None:
        params["$top"] = str(top)
    if skip is not None:
        params["$skip"] = str(skip)
    if order_by:
        params["$orderby"] = order_by
    if count:
        params["$count"] = "true"
    return params


def extract_value_and_count(response: dict) -> tuple[list[dict], Optional[int]]:
    """Extract the items array and optional count from a list response.

    Supports both OData v4 (``value`` / ``@odata.count``) and the Agent Memory
    service format (``data`` / ``count``).

    Args:
        response: The parsed JSON response from a list endpoint.

    Returns:
        A tuple of (list of item dicts, total count or None).
    """
    # OData v4 standard uses "value" key; fall back to "data" for compatibility
    items: list[dict] = response.get("value", response.get("data", []))
    total: Optional[int] = response.get(
        "@odata.count", response.get("@count", response.get("count"))
    )
    return items, total
