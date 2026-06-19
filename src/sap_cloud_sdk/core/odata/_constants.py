"""Shared constants for the OData v4 HTTP layer."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------

CSRF_HEADER = "X-CSRF-Token"
CSRF_FETCH_VALUE = "Fetch"
CSRF_FETCH_TIMEOUT = 10

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT = 30

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

DEFAULT_HEADERS: dict[str, str] = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# HTTP method literals
GET = "GET"
POST = "POST"
PUT = "PUT"
PATCH = "PATCH"
DELETE = "DELETE"

# Standard conditional-request header
IF_MATCH_HEADER = "If-Match"

# ---------------------------------------------------------------------------
# OData system query options
# ---------------------------------------------------------------------------

QUERY_SELECT = "$select"
QUERY_FILTER = "$filter"
QUERY_ORDERBY = "$orderby"
QUERY_TOP = "$top"
QUERY_SKIP = "$skip"
QUERY_EXPAND = "$expand"

# ---------------------------------------------------------------------------
# OData response envelope keys
# ---------------------------------------------------------------------------

RESPONSE_VALUE = "value"
RESPONSE_NEXT_LINK = "@odata.nextLink"
