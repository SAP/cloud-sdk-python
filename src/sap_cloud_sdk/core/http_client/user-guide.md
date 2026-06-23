# HTTP Client User Guide

This module provides a general-purpose HTTP client for calling target systems described by BTP Destinations. It handles auth-header injection, typed exceptions, and telemetry automatically.

```python
from sap_cloud_sdk.core.http_client import (
    HttpClient,
    http_client_for_destination,
    HttpClientError,
    HttpConnectionError,
    HttpNotFoundError,
    HttpResponseError,
    HttpUnauthorizedError,
)
```

## Destination integration

`http_client_for_destination` builds an `HttpClient` from a resolved BTP `Destination`. The destination's auth tokens, ERP headers, and `URL.headers.*` properties are pre-baked into the underlying `requests.Session`, so no manual header management is needed.

```python
from sap_cloud_sdk.destination import create_client
from sap_cloud_sdk.core.http_client import http_client_for_destination

dest_client = create_client()
dest = dest_client.get_destination("MY_API")

http = http_client_for_destination(dest)
response = http.get("/api/v1/resources")
data = response.json()
```

> **Note:** Use a destination fetched via `get_destination()` (v2 API), which populates `auth_tokens`. Destinations from the deprecated v1 methods do not carry pre-fetched tokens.

When the destination URL points to a host root rather than the service root, pass `sub_path`:

```python
http = http_client_for_destination(dest, sub_path="api/v1")
response = http.get("/resources")  # calls https://host/api/v1/resources
```

## Direct construction

Inject any `requests.Session` directly when not using BTP Destinations:

```python
import requests
from sap_cloud_sdk.core.http_client import HttpClient

session = requests.Session()
session.headers["Authorization"] = "Bearer <token>"

http = HttpClient(base_url="https://api.example.com", session=session)
```

## HTTP methods

All convenience methods raise typed exceptions on non-2xx responses and record telemetry automatically.

```python
# GET — with optional query parameters
response = http.get("/items", params={"$top": "10", "status": "active"})

# POST — JSON body
response = http.post("/items", json={"name": "new item", "type": "A"})

# PUT — full replacement
response = http.put("/items/1", json={"name": "updated item"})

# PATCH — partial update
response = http.patch("/items/1", json={"status": "inactive"})

# DELETE
response = http.delete("/items/1")

# Low-level request — does NOT raise on non-2xx; caller inspects the response
response = http.request("GET", "/items")
if not response.ok:
    ...
```

### Extra headers per request

Pass `headers=` to add or override headers for a single call:

```python
response = http.get("/items", headers={"X-Correlation-ID": "abc123"})
```

Per-request headers are merged on top of the session defaults.

### Raw body

Use `data=` for non-JSON payloads:

```python
response = http.post("/upload", data=b"raw bytes", headers={"Content-Type": "application/octet-stream"})
```

## What headers are pre-baked

When `http_client_for_destination` builds the client it calls `dest.get_headers()`, which injects the following into the session:

1. **ERP headers** — `sap-client` and `sap-language` from destination properties (if present)
2. **`URL.headers.*` properties** — any destination property prefixed with `URL.headers.` becomes a header (e.g. `URL.headers.apiKey = secret` → `apiKey: secret`)
3. **Auth tokens** — pre-fetched by BTP and returned in `dest.auth_tokens`; each token's `http_header` dict is injected directly (e.g. `Authorization: Bearer eyJ...`)

Auth tokens take precedence over `URL.headers.*` when both set the same key.

## Error handling

```python
from sap_cloud_sdk.core.http_client import (
    http_client_for_destination,
    HttpNotFoundError,
    HttpUnauthorizedError,
    HttpResponseError,
    HttpConnectionError,
)

http = http_client_for_destination(dest)

try:
    response = http.get("/items/123")
except HttpNotFoundError:
    print("item not found")
except HttpUnauthorizedError as e:
    print(f"auth failure (HTTP {e.status_code}): check destination configuration")
except HttpResponseError as e:
    print(f"service error (HTTP {e.status_code})")
except HttpConnectionError:
    print("network unreachable — no response received")
```

Exception hierarchy:

```
HttpClientError
├── HttpResponseError       # non-2xx HTTP response (carries .status_code and .response)
│   ├── HttpNotFoundError   # 404
│   └── HttpUnauthorizedError  # 401 / 403
└── HttpConnectionError     # network failure — no HTTP response received
```

`HttpResponseError` exposes:
- `.status_code: int` — the HTTP status code
- `.response` — the raw `requests.Response` object
