# Proposal: Shared OData Client Abstractions for SAP Cloud SDK Python

## Overview

Introduce a `core/odata/` subpackage (and a top-level `odata/` convenience module) that provides reusable, protocol-aware building blocks for OData v4 communication. These abstractions serve two consumers simultaneously: the hand-written service modules that already speak OData (DMS, ADMS) and the forthcoming OData code generator whose emitted clients will import from this package.

---

## Motivation

The SDK currently contains at least two modules (DMS, ADMS) that speak OData v4 and one empty placeholder (`odata/`). Each has written its own HTTP transport, query parameter logic, and response parsing. This creates:

- **Duplication** — filter encoding, `$select`/`$expand` serialization, CSRF token handling, and error mapping are re-implemented per module.
- **Inconsistency** — subtle behavioral differences accumulate (e.g., error handling, pagination strategy).
- **Maintenance burden** — a bug fix or protocol improvement must be applied in multiple places.
- **No foundation for generation** — the planned code generator needs stable, well-tested base classes to import from; it cannot generate the transport layer itself.

A shared `odata` layer resolves all of this and is a prerequisite for the code generation proposal.

---

## Scope

| In scope | Out of scope |
|---|---|
| OData v4 query builder (`$filter`, `$select`, `$orderby`, `$top`, `$skip`, `$expand`) | OData v2 support (phase 2) |
| Typed request builder classes (GetAll, GetByKey, Create, Update, Delete) | Batch requests (phase 2) |
| Synchronous HTTP transport (`ODataHttpTransport`) | Actions / function imports (phase 2) |
| Async HTTP transport (`AsyncODataHttpTransport`) | GraphQL / non-OData protocols |
| Response deserialization (JSON → dataclass) | ORM-style change tracking |
| OData-specific exception hierarchy | Caching layer |
| CSRF token fetch-and-retry | Streaming / chunked responses |
| Destination integration | Custom serialization formats (XML, Atom) |
| Pagination helpers (server-driven `@odata.nextLink`) | |
| `py.typed` marker, full type annotations | |

---

## Module Layout

```
src/sap_cloud_sdk/
├── core/
│   └── odata/                         # Internal, reusable implementation
│       ├── __init__.py
│       ├── _transport.py              # ODataHttpTransport (sync)
│       ├── _async_transport.py        # AsyncODataHttpTransport
│       ├── _query.py                  # StructuredQuery builder
│       ├── _filter.py                 # Filter expression DSL
│       ├── _request_builders.py       # GetAllRequestBuilder, GetByKeyRequestBuilder, ...
│       ├── _response.py               # ODataResponse, deserializer
│       ├── _csrf.py                   # CSRF token fetch/cache
│       ├── _pagination.py             # Pagination iterator
│       ├── _models.py                 # Protocol-level types (ODataEntity, etc.)
│       └── exceptions.py             # OData exception hierarchy
└── odata/                             # Public convenience re-export
    ├── __init__.py                    # __all__ surface for external consumers
    └── py.typed
```

The `core/odata/` location follows the established pattern of `core/telemetry/` and `core/secret_resolver/` — shared infrastructure that other modules depend on. The top-level `odata/` module is a thin re-export for external consumers and the generator's emitted `import` statements.

---

## Public API

```python
# sap_cloud_sdk/odata/__init__.py
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata._async_transport import AsyncODataHttpTransport
from sap_cloud_sdk.core.odata._request_builders import (
    GetAllRequestBuilder,
    GetByKeyRequestBuilder,
    CreateRequestBuilder,
    UpdateRequestBuilder,
    DeleteRequestBuilder,
)
from sap_cloud_sdk.core.odata._query import StructuredQuery, OrderDirection
from sap_cloud_sdk.core.odata._filter import FilterExpression
from sap_cloud_sdk.core.odata._models import ODataEntity
from sap_cloud_sdk.core.odata.exceptions import (
    ODataError,
    ODataRequestError,
    ODataNotFoundError,
    ODataAuthError,
    ODataDeserializationError,
)

__all__ = [
    "ODataHttpTransport",
    "AsyncODataHttpTransport",
    "GetAllRequestBuilder",
    "GetByKeyRequestBuilder",
    "CreateRequestBuilder",
    "UpdateRequestBuilder",
    "DeleteRequestBuilder",
    "StructuredQuery",
    "OrderDirection",
    "FilterExpression",
    "ODataEntity",
    "ODataError",
    "ODataRequestError",
    "ODataNotFoundError",
    "ODataAuthError",
    "ODataDeserializationError",
]
```

---

## Key Components

### 1. `ODataHttpTransport` — HTTP Layer

Owns the `requests.Session`, OAuth2 token lifecycle, CSRF handling, and base URL management. Designed for injection into request builders.

```python
# core/odata/_transport.py
from __future__ import annotations
import logging
from typing import Any
import requests
from sap_cloud_sdk.core.odata.exceptions import ODataError, ODataAuthError, ODataRequestError
from sap_cloud_sdk.core.odata._csrf import CsrfTokenProvider

logger = logging.getLogger(__name__)

class ODataHttpTransport:
    """Reusable HTTP transport for OData v4 services.

    Args:
        base_url: Root URL of the OData service (e.g. https://host/sap/opu/odata4/svc/).
        session: Authenticated requests.Session (OAuth2 or mTLS configured externally).
        csrf_enabled: Whether to fetch and send CSRF tokens on mutating requests.

    Example:
        >>> transport = ODataHttpTransport(
        ...     base_url="https://example.com/odata/v4/",
        ...     session=oauth_session,
        ... )
    """

    def __init__(
        self,
        base_url: str,
        session: requests.Session,
        csrf_enabled: bool = True,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._csrf = CsrfTokenProvider(self) if csrf_enabled else None

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GET request and return parsed JSON body."""
        ...

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Execute a POST with CSRF token, return parsed JSON."""
        ...

    def patch(self, path: str, body: dict[str, Any], etag: str | None = None) -> dict[str, Any]:
        """Execute a PATCH (update) with CSRF token and optional ETag."""
        ...

    def delete(self, path: str, etag: str | None = None) -> None:
        """Execute a DELETE with CSRF token and optional ETag."""
        ...

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.status_code == 401:
            raise ODataAuthError(response)
        if response.status_code == 404:
            from sap_cloud_sdk.core.odata.exceptions import ODataNotFoundError
            raise ODataNotFoundError(response)
        if not response.ok:
            raise ODataRequestError(response)
```

**`AsyncODataHttpTransport`** mirrors this interface using `httpx.AsyncClient` (already a project dependency). Both are created from a `Destination` via a shared factory:

```python
from sap_cloud_sdk.odata import ODataHttpTransport
from sap_cloud_sdk.destination import Destination

def odata_transport_from_destination(destination: Destination) -> ODataHttpTransport:
    """Build an ODataHttpTransport from a resolved BTP Destination."""
    ...
```

---

### 2. `StructuredQuery` — Query Builder

A fluent, immutable query builder that serialises OData system query options. All methods return a new `StructuredQuery` instance (no mutation).

```python
# core/odata/_query.py
from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._filter import FilterExpression

class OrderDirection(Enum):
    ASC = "asc"
    DESC = "desc"

class StructuredQuery:
    """Immutable OData v4 query parameter builder.

    Example:
        >>> query = (
        ...     StructuredQuery()
        ...     .select("BusinessPartnerID", "DisplayName")
        ...     .filter(FilterExpression.field("DisplayName").eq("Acme"))
        ...     .order_by("DisplayName", OrderDirection.ASC)
        ...     .top(20)
        ...     .skip(0)
        ...     .expand("ToAddresses")
        ... )
        >>> query.to_params()
        {
            "$select": "BusinessPartnerID,DisplayName",
            "$filter": "DisplayName eq 'Acme'",
            "$orderby": "DisplayName asc",
            "$top": "20",
            "$skip": "0",
            "$expand": "ToAddresses",
        }
    """

    def select(self, *fields: str) -> StructuredQuery: ...
    def filter(self, expression: FilterExpression) -> StructuredQuery: ...
    def order_by(self, field: str, direction: OrderDirection = OrderDirection.ASC) -> StructuredQuery: ...
    def top(self, n: int) -> StructuredQuery: ...
    def skip(self, n: int) -> StructuredQuery: ...
    def expand(self, *nav_properties: str) -> StructuredQuery: ...
    def custom(self, key: str, value: str) -> StructuredQuery: ...
    def to_params(self) -> dict[str, str]: ...
```

---

### 3. `FilterExpression` — Filter DSL

A lightweight, type-safe expression builder that avoids string manipulation in user code.

```python
# core/odata/_filter.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class FilterExpression:
    """Composable OData $filter expression.

    Example:
        >>> f = (
        ...     FilterExpression.field("Price").gt(100)
        ...     .and_(FilterExpression.field("Category").eq("Books"))
        ... )
        >>> str(f)
        "(Price gt 100) and (Category eq 'Books')"
    """

    _expr: str

    @staticmethod
    def field(name: str) -> _FieldRef: ...

    def and_(self, other: FilterExpression) -> FilterExpression: ...
    def or_(self, other: FilterExpression) -> FilterExpression: ...
    def not_(self) -> FilterExpression: ...
    def __str__(self) -> str:
        return self._expr


class _FieldRef:
    """Intermediate: a field name awaiting a comparison operator."""
    def __init__(self, name: str) -> None: ...
    def eq(self, value: Any) -> FilterExpression: ...
    def ne(self, value: Any) -> FilterExpression: ...
    def lt(self, value: Any) -> FilterExpression: ...
    def le(self, value: Any) -> FilterExpression: ...
    def gt(self, value: Any) -> FilterExpression: ...
    def ge(self, value: Any) -> FilterExpression: ...
    def contains(self, value: str) -> FilterExpression: ...
    def starts_with(self, value: str) -> FilterExpression: ...
    def ends_with(self, value: str) -> FilterExpression: ...
```

---

### 4. Request Builders — CRUD Operations

Generic, entity-type-parametrised builders. These are the types the code generator imports and instantiates.

```python
# core/odata/_request_builders.py
from __future__ import annotations
from typing import Generic, TypeVar, TYPE_CHECKING
from ._query import StructuredQuery
from ._response import deserialize_collection, deserialize_single

if TYPE_CHECKING:
    from ._transport import ODataHttpTransport

T = TypeVar("T")


class GetAllRequestBuilder(Generic[T]):
    """Fluent builder for OData GetAll (collection) requests.

    Example:
        >>> results = (
        ...     GetAllRequestBuilder(transport, BusinessPartner)
        ...     .select("BusinessPartnerID", "DisplayName")
        ...     .filter(FilterExpression.field("DisplayName").contains("Acme"))
        ...     .top(50)
        ...     .execute()
        ... )
    """

    def __init__(self, transport: ODataHttpTransport, entity_type: type[T]) -> None: ...

    def select(self, *fields: str) -> GetAllRequestBuilder[T]:
        """Restrict returned fields via $select."""
        ...

    def filter(self, expression: FilterExpression) -> GetAllRequestBuilder[T]:
        """Apply $filter expression."""
        ...

    def order_by(self, field: str, direction: OrderDirection = OrderDirection.ASC) -> GetAllRequestBuilder[T]:
        ...

    def top(self, n: int) -> GetAllRequestBuilder[T]: ...
    def skip(self, n: int) -> GetAllRequestBuilder[T]: ...
    def expand(self, *nav_properties: str) -> GetAllRequestBuilder[T]: ...

    def execute(self) -> list[T]:
        """Execute the request and return all matching entities."""
        ...

    def iterate_pages(self) -> Iterator[list[T]]:
        """Yield pages using server-driven pagination (@odata.nextLink)."""
        ...

    def iterate_entities(self) -> Iterator[T]:
        """Yield individual entities across all pages (memory-efficient)."""
        ...


class GetByKeyRequestBuilder(Generic[T]):
    def __init__(
        self,
        transport: ODataHttpTransport,
        entity_type: type[T],
        key: dict[str, Any],
    ) -> None: ...

    def select(self, *fields: str) -> GetByKeyRequestBuilder[T]: ...
    def expand(self, *nav_properties: str) -> GetByKeyRequestBuilder[T]: ...

    def execute(self) -> T:
        """Execute and return the single entity, raising ODataNotFoundError if absent."""
        ...


class CreateRequestBuilder(Generic[T]):
    def __init__(self, transport: ODataHttpTransport, entity: T) -> None: ...
    def execute(self) -> T: ...


class UpdateRequestBuilder(Generic[T]):
    def __init__(self, transport: ODataHttpTransport, entity: T) -> None: ...
    def replace(self) -> UpdateRequestBuilder[T]:
        """Switch from PATCH (default) to PUT (full replacement)."""
        ...
    def execute(self) -> T: ...


class DeleteRequestBuilder(Generic[T]):
    def __init__(
        self,
        transport: ODataHttpTransport,
        entity_type: type[T],
        key: dict[str, Any],
    ) -> None: ...
    def execute(self) -> None: ...
```

Async variants (`AsyncGetAllRequestBuilder`, etc.) mirror this API with `async def execute()`.

---

### 5. Exception Hierarchy

```python
# core/odata/exceptions.py

class ODataError(Exception):
    """Base for all OData-related errors."""

class ODataRequestError(ODataError):
    """HTTP-level error from an OData service (non-2xx response)."""
    def __init__(self, response: requests.Response) -> None:
        self.status_code = response.status_code
        self.response = response
        super().__init__(f"OData request failed: HTTP {response.status_code}")

class ODataNotFoundError(ODataRequestError):
    """Entity not found (HTTP 404)."""

class ODataAuthError(ODataRequestError):
    """Authentication / authorization failure (HTTP 401/403)."""

class ODataDeserializationError(ODataError):
    """Failed to deserialize an OData response payload."""

class ODataCsrfError(ODataError):
    """Failed to fetch or validate CSRF token."""
```

---

### 6. Pagination

Server-driven pagination via `@odata.nextLink` is encapsulated in `_pagination.py` and surfaced through `iterate_pages()` / `iterate_entities()` on `GetAllRequestBuilder`. Consumers never need to inspect `@odata.nextLink` themselves.

```python
# core/odata/_pagination.py
from __future__ import annotations
from typing import Generic, TypeVar, Iterator, Callable, Any

T = TypeVar("T")

class ODataPageIterator(Generic[T]):
    """Consumes @odata.nextLink to yield pages lazily.

    Args:
        fetch_page: Callable that takes a URL and returns a raw JSON dict.
        entity_type: Dataclass to deserialize each item into.
        first_url: The initial request URL (already including query params).
    """

    def __init__(
        self,
        fetch_page: Callable[[str], dict[str, Any]],
        entity_type: type[T],
        first_url: str,
    ) -> None: ...

    def __iter__(self) -> Iterator[list[T]]: ...
```

---

## Migration Path for DMS and ADMS

Both modules should be migrated to use `core/odata/` rather than their bespoke HTTP layers. This is a refactor-only change with no public API breakage:

1. Replace module-local `_http.py` OData logic with `ODataHttpTransport`.
2. Replace hand-written query string construction with `StructuredQuery`.
3. Replace custom response parsing with `deserialize_collection` / `deserialize_single`.
4. Extend `ODataError` instead of module-local exception base classes.

The migration can be done incrementally: one module at a time, guarded by existing test suites.

---

## Design Decisions

### Composition over inheritance
Request builders are standalone classes, not methods on a base `ODataClient`. This keeps the surface area small and lets generated clients use exactly the builders they need.

### Immutable query builder
`StructuredQuery` returns new instances on each call. This prevents shared-state bugs when a base query is reused across multiple requests (common in service facades).

### No ORM / change-tracking
The SDK's guidelines prefer minimal complexity. Change-tracking (dirty-flag per field, automatic diff on update) is powerful but expensive to maintain. Callers construct and pass full entity objects explicitly.

### `requests` for sync, `httpx` for async
`requests` is already a declared dependency and used across the SDK. `httpx` is also already a dependency and is the natural fit for async. Both are wrapped inside the transport classes so consumers never import them directly.

### CSRF handling is opt-in per transport instance
Some OData services require CSRF tokens; others do not. The `csrf_enabled` flag on `ODataHttpTransport` lets modules opt out without monkey-patching.

### Destination integration is a factory, not a base class
Following the guidelines' preference for composition: `odata_transport_from_destination(destination)` is a free function, not a mixin or inherited constructor.

---

## Telemetry

The shared transport emits spans for every HTTP call using the existing `@record_metrics` decorator pattern. Modules that build on top can pass their own `Module` constant via the `_telemetry_source` parameter already established by the guidelines.

---

## Dependencies

No new runtime dependencies. All required packages are already declared:

| Package | Already in `pyproject.toml` | Usage |
|---|---|---|
| `requests` | Yes | Sync HTTP |
| `httpx` | Yes | Async HTTP |
| `pydantic` | Yes | Response validation |

---

## Testing Strategy

| Layer | Approach |
|---|---|
| `StructuredQuery` | Pure unit tests — input combinations → expected `to_params()` output |
| `FilterExpression` | Pure unit tests — expression trees → expected `$filter` strings |
| `ODataHttpTransport` | Unit tests with `responses` or `unittest.mock` patching `requests.Session` |
| CSRF handling | Unit tests simulating 403+fetch-token+retry cycle |
| Pagination | Unit tests with multi-page mock responses |
| Request builders | Unit tests asserting correct URL + params + body construction |
| DMS / ADMS integration | Existing integration test suites confirm no regression after migration |

Test file layout mirrors source:

```
tests/
└── core/
    └── unit/
        └── odata/
            ├── test_structured_query.py
            ├── test_filter_expression.py
            ├── test_transport.py
            ├── test_csrf.py
            ├── test_pagination.py
            └── test_request_builders.py
```

---

## Phasing

### Phase 1 — Foundation
- `StructuredQuery` + `FilterExpression`
- `ODataHttpTransport` (sync) + CSRF handling
- `ODataPageIterator`
- Exception hierarchy
- `GetAllRequestBuilder`, `GetByKeyRequestBuilder`
- Full unit test suite

### Phase 2 — Mutations + async
- `CreateRequestBuilder`, `UpdateRequestBuilder`, `DeleteRequestBuilder`
- `AsyncODataHttpTransport` + async request builder variants
- `odata_transport_from_destination()` factory

### Phase 3 — Migration
- Migrate DMS to use shared abstractions
- Migrate ADMS to use shared abstractions
- Remove now-redundant bespoke OData code from each module

### Phase 4 — Generator integration
- Generator emits `from sap_cloud_sdk.odata import ...` imports
- End-to-end test: generate client from sample EDMX, execute against mock server

---

## Open Questions

1. **`ODataEntity` base class vs. plain dataclass**: Should generated entity classes inherit from a common `ODataEntity` base (enabling generic reflection on `_entity_set`, `_key_fields`)? Or keep them as plain dataclasses with `ClassVar` annotations? Inheritance is convenient for the transport layer's generic serializer; plain dataclasses are simpler and more aligned with "composition over inheritance."

2. **ETag / optimistic locking**: Should `UpdateRequestBuilder` and `DeleteRequestBuilder` track ETags automatically, or require callers to pass them explicitly? Automatic tracking couples the transport to entity state; explicit is simpler but chattier.

3. **`$count` support**: Should `GetAllRequestBuilder.count()` be a separate terminal operation returning `int`, or part of the standard response object?

4. **Coexistence with `odata/` placeholder**: The existing empty `src/sap_cloud_sdk/odata/` directory suggests intent. This proposal uses it as the public re-export surface. Confirm this aligns with the original placeholder intent before implementation.
