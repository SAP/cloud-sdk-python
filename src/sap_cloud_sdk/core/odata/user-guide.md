# OData Core User Guide

This module provides shared, reusable OData v4 building blocks for service modules and generated clients within the SAP Cloud SDK for Python.

It is an internal package (`core/odata`). Import from it directly:

```python
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata._request_builders import GetAllRequestBuilder
from sap_cloud_sdk.core.odata._filter import FilterExpression
from sap_cloud_sdk.core.odata._query import StructuredQuery, OrderDirection
from sap_cloud_sdk.core.odata._factory import odata_transport_from_destination
from sap_cloud_sdk.core.odata.exceptions import ODataError, ODataNotFoundError
```

## Destination integration

`odata_transport_from_destination` builds an `ODataHttpTransport` from a resolved BTP Destination.  The destination's auth tokens and ERP headers are pre-baked into the underlying session, so no manual header management is needed.

```python
from sap_cloud_sdk.destination import create_client
from sap_cloud_sdk.core.odata._factory import odata_transport_from_destination
from sap_cloud_sdk.core.odata._request_builders import GetAllRequestBuilder

dest_client = create_client()
destination = dest_client.get_destination("S4HANA_OData")

transport = odata_transport_from_destination(destination)
results = GetAllRequestBuilder(transport, BusinessPartner).top(10).execute()
```

When the destination URL points to the host root rather than the OData service root, pass `odata_path`:

```python
transport = odata_transport_from_destination(
    destination,
    odata_path="sap/opu/odata4/svc/API_BUSINESS_PARTNER/",
)
```

Set `csrf_enabled=False` for services that do not require CSRF tokens:

```python
transport = odata_transport_from_destination(destination, csrf_enabled=False)
```

## Transport

`ODataHttpTransport` wraps a `requests.Session` and handles JSON serialisation, CSRF token fetch-and-retry, and status-code–to-exception mapping.

```python
import requests
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport

session = requests.Session()
session.headers["Authorization"] = "Bearer <token>"

transport = ODataHttpTransport(
    base_url="https://host/sap/opu/odata4/svc/",
    session=session,
)
```

Set `csrf_enabled=False` for services that do not require CSRF tokens:

```python
transport = ODataHttpTransport(base_url="...", session=session, csrf_enabled=False)
```

### Async transport

`AsyncODataHttpTransport` mirrors the sync interface using `httpx.AsyncClient`:

```python
import httpx
from sap_cloud_sdk.core.odata._async_transport import AsyncODataHttpTransport

async with AsyncODataHttpTransport(
    base_url="https://host/sap/opu/odata4/svc/",
    client=httpx.AsyncClient(headers={"Authorization": "Bearer <token>"}),
) as transport:
    data = await transport.request("GET", "EntitySet", params={"$top": "10"})
```

## Request Builders

Request builders compose a transport, an entity type, and optional query options into a typed, fluent API.

### GetAllRequestBuilder

```python
from sap_cloud_sdk.core.odata._request_builders import GetAllRequestBuilder
from sap_cloud_sdk.core.odata._filter import FilterExpression
from sap_cloud_sdk.core.odata._query import OrderDirection

results = (
    GetAllRequestBuilder(transport, BusinessPartner)
    .select("BusinessPartnerID", "DisplayName")
    .filter(FilterExpression.field("DisplayName").contains("Acme"))
    .order_by("DisplayName", OrderDirection.ASC)
    .top(50)
    .execute()
)
```

### GetByKeyRequestBuilder

```python
from sap_cloud_sdk.core.odata._request_builders import GetByKeyRequestBuilder

partner = (
    GetByKeyRequestBuilder(transport, BusinessPartner, {"BusinessPartnerID": "1000001"})
    .expand("ToAddresses")
    .execute()
)
```

Raises `ODataNotFoundError` when the entity does not exist.

### CreateRequestBuilder

```python
from sap_cloud_sdk.core.odata._request_builders import CreateRequestBuilder

new_partner = BusinessPartner(BusinessPartnerID="", DisplayName="New Corp")
created = CreateRequestBuilder(transport, new_partner).execute()
```

### UpdateRequestBuilder

PATCH (partial update) by default; call `.replace()` to switch to PUT:

```python
from sap_cloud_sdk.core.odata._request_builders import UpdateRequestBuilder

# PATCH
updated = UpdateRequestBuilder(transport, partner).execute()

# PUT — full replacement
updated = UpdateRequestBuilder(transport, partner).replace().execute()

# With ETag for optimistic locking
updated = UpdateRequestBuilder(transport, partner, etag='"W/\\"1234\\""').execute()
```

### DeleteRequestBuilder

```python
from sap_cloud_sdk.core.odata._request_builders import DeleteRequestBuilder

DeleteRequestBuilder(transport, BusinessPartner, {"BusinessPartnerID": "1000001"}).execute()
```

## FilterExpression

Build `$filter` expressions without string manipulation:

```python
from sap_cloud_sdk.core.odata._filter import FilterExpression

# Simple comparison
f = FilterExpression.field("Price").gt(100)
str(f)  # "Price gt 100"

# Combine with and_ / or_ / not_
f = (
    FilterExpression.field("Price").gt(100)
    .and_(FilterExpression.field("Category").eq("Books"))
)
str(f)  # "(Price gt 100) and (Category eq 'Books')"

# String functions
f = FilterExpression.field("Name").contains("Acme")
str(f)  # "contains(Name, 'Acme')"
```

Available operators: `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `contains`, `starts_with`, `ends_with`.

## StructuredQuery

Immutable query builder — each method returns a new instance, safe to share:

```python
from sap_cloud_sdk.core.odata._query import StructuredQuery, OrderDirection

base = StructuredQuery().select("ID", "Name").top(20)
page1 = base.skip(0)
page2 = base.skip(20)

page1.to_params()
# {"$select": "ID,Name", "$top": "20", "$skip": "0"}
```

Pass the result directly to a transport call or a request builder.

## Pagination

Server-driven pagination via `@odata.nextLink` is built into `GetAllRequestBuilder`:

```python
# Yield pages lazily
for page in builder.iterate_pages():
    for entity in page:
        process(entity)

# Or flatten across all pages
for entity in builder.iterate_entities():
    process(entity)
```

`ODataPageIterator` can also be used directly when you manage the transport call yourself:

```python
from sap_cloud_sdk.core.odata._pagination import ODataPageIterator

iterator = ODataPageIterator(
    fetch_page=lambda url: transport.request("GET", url.removeprefix(transport._base_url + "/")),
    entity_type=BusinessPartner,
    first_url=transport.absolute_url("BusinessPartnerSet?$top=100"),
)
for page in iterator:
    ...
```

## Entity Model

Entity dataclasses declare metadata via `ClassVar` annotations so the transport layer can reflect on key fields and entity-set names:

```python
from dataclasses import dataclass
from typing import ClassVar
from sap_cloud_sdk.core.odata._models import ODataEntity

@dataclass
class BusinessPartner(ODataEntity):
    _entity_set: ClassVar[str] = "BusinessPartnerSet"
    _key_fields: ClassVar[list[str]] = ["BusinessPartnerID"]

    BusinessPartnerID: str = ""
    DisplayName: str = ""
```

Plain dataclasses (without `ODataEntity`) also work — `_entity_set` defaults to the class name and request builders that need key fields will raise `ValueError` if `_key_fields` is absent.

## Error Handling

```python
from sap_cloud_sdk.core.odata.exceptions import (
    ODataError,
    ODataRequestError,
    ODataNotFoundError,
    ODataAuthError,
    ODataDeserializationError,
    ODataCsrfError,
)

try:
    partner = GetByKeyRequestBuilder(transport, BusinessPartner, key).execute()
except ODataNotFoundError:
    ...
except ODataAuthError as e:
    print(f"Auth failure (HTTP {e.status_code})")
except ODataCsrfError as e:
    print(f"CSRF handshake failed: {e}")
except ODataRequestError as e:
    print(f"Service error (HTTP {e.status_code}): {e}")
except ODataDeserializationError as e:
    print(f"Could not parse response: {e}")
except ODataError:
    ...
```

Exception hierarchy:

```
ODataError
├── ODataRequestError       # non-2xx HTTP response
│   ├── ODataNotFoundError  # 404
│   └── ODataAuthError      # 401 / 403
├── ODataDeserializationError
└── ODataCsrfError
```
