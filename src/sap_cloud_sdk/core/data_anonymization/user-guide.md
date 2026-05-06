# Data Anonymization User Guide

This module provides a unified API for anonymizing and pseudonymizing text and
files that contain personally identifiable information (PII). The module
contains a factory function, typed request/result dataclasses, a transport
abstraction, and automatic credential loading from service bindings.

The module handles configuration, request construction, mTLS
client-certificate authentication, HTTP transport, and operation-level
telemetry so developers can focus on business logic while satisfying
data-privacy requirements. Telemetry is limited to aggregate operation
metrics and excludes request and response payloads.

## Installation

The data anonymization module is part of the SAP Cloud SDK for Python and is
available automatically once the SDK is installed.

## Import

Import what you need explicitly:

```python
from sap_cloud_sdk.core.data_anonymization import (
    create_client,
    AnonymizeTextRequest,
    AnonymizeFileRequest,
    PseudonymizeTextRequest,
    PseudonymizeFileRequest,
)
```

Or use a star import for convenience:

```python
from sap_cloud_sdk.core.data_anonymization import *
```

## Quick Start

### Auto-detected configuration (cloud / BTP)

Use `create_client()` without arguments. The factory loads credentials from the secret mount or the `CLOUD_SDK_CFG` environment variable (service name `data-anonymization`).

```python
from sap_cloud_sdk.core.data_anonymization import (
    create_client,
    AnonymizeTextRequest,
    PseudonymizeTextRequest,
)

client = create_client()

# Anonymize – irreversible PII removal
result = client.anonymize_text(
    AnonymizeTextRequest(
        text="Please contact John Doe at john@example.com"
    )
)
assert result.result is not None

# Pseudonymize – reversible token replacement
pseudo = client.pseudonymize_text(
    PseudonymizeTextRequest(text="John Doe lives at 42 Main St")
)
assert pseudo.result is not None
assert len(pseudo.metadata) >= 0
```

### Explicit configuration

Pass a `DataAnonymizationConfig` directly when the base64-encoded client certificate values are known at code time.

```python
from sap_cloud_sdk.core.data_anonymization import (
    create_client, DataAnonymizationConfig,
)

config = DataAnonymizationConfig(
    service_url="https://anonymization.example.com",
    cert="<base64-encoded-client-certificate>",
    key="<base64-encoded-client-private-key>",
)

client = create_client(config=config)
```

## Authentication

Authentication uses a **Key Store (mTLS client certificate)** exclusively. Two sources are supported, selected automatically from the fields set in `DataAnonymizationConfig`.

### Inline Key Store

Set `cert` and `key` to base64-encoded PEM values. The transport decodes them and writes temporary files that are attached to every outgoing HTTP request.

```python
from sap_cloud_sdk.core.data_anonymization import DataAnonymizationConfig

config = DataAnonymizationConfig(
    service_url="https://anonymization.example.com",
    cert="<base64-encoded-client-certificate>",
    key="<base64-encoded-client-private-key>",
)
```

Both fields must be provided together — setting one without the other raises a `ValueError`.

### BTP Destination Key Store (recommended for cloud deployments)

Set `destination_name` to the name of a BTP Destination configured with `ClientCertificateAuthentication`. The transport resolves the destination at runtime using `sap_cloud_sdk.destination`, reads its `KeyStoreLocation`, and then fetches the referenced certificate bundle from the Destination certificate API.

The referenced certificate content is expected to be a PEM bundle containing the private key together with the certificate chain. Base64-encoded PEM content is also supported.

```python
from sap_cloud_sdk.core.data_anonymization import DataAnonymizationConfig

config = DataAnonymizationConfig(
    service_url="https://anonymization.example.com",
    destination_name="my-anonymization-cert-dest",
)
```

At least one Key Store source must be configured. Providing neither raises a `ValueError` during config construction.

## Operations

### Text anonymization

Irreversible. All detected PII entities are replaced with category placeholders (e.g. `[PERSON]`, `[EMAIL]`, `[PHONE]`). The original values cannot be recovered.

```python
from sap_cloud_sdk.core.data_anonymization import (
    create_client, AnonymizeTextRequest,
)

client = create_client()

request = AnonymizeTextRequest(
    text="Employee Alice Smith (alice@corp.com, +1-555-0100) submitted the report.",
    entities=["profile-person", "profile-email", "profile-phone"],
    allowlist="Alice Smith",
    enable_default_allowlist=False
)

result = client.anonymize_text(request)
assert result.result is not None
```

**Required fields:**
- `text` – must not be empty.

**Optional fields:**
- `entities` – list of entity profiles in priority order.
- `anonymization_method_per_profile` – JSON string matching the OpenAPI field
  `anonymization-method-per-profile`.
- `allowlist` – semicolon-separated allowlist entries.
- `enable_default_allowlist` – include the service default allowlist.
- `custom_entities` – JSON string of custom entity regex definitions.

### Text pseudonymization

Reversible. Each PII entity is replaced with a consistent token. The mapping between original values and tokens is returned in `metadata` so an authorised party can de-pseudonymize later.

```python
from sap_cloud_sdk.core.data_anonymization import (
    create_client, PseudonymizeTextRequest,
)

client = create_client()

request = PseudonymizeTextRequest(
    text="Customer Bob Brown (bob@example.com) placed order #9981.",
    entities=["profile-person", "profile-email"],
    pseudonymization_secret="12345678901234567890123456789012",
)

pseudo = client.pseudonymize_text(request)
for mapping in pseudo.metadata:
    assert mapping.entity_type is not None
```

**Required fields:**
- `text` – must not be empty.

**Optional fields:**
- All common text parameters from anonymization.
- `pseudonymization_metadata` – optional metadata JSON string.
- `pseudonymization_secret` – deterministic secret, minimum 32 characters.

### File anonymization

Use `AnonymizeFileRequest` for multipart uploads. Exactly one of `file_path` or
`file_content` must be provided.

```python
from sap_cloud_sdk.core.data_anonymization import (
    create_client,
    AnonymizeFileRequest,
)

client = create_client()

request = AnonymizeFileRequest(
    file_path="sample.pdf",
    entities=["profile-person", "profile-email"]
)

result = client.anonymize_file(request)

if result.result:
    assert result.result is not None
else:
    assert result.raw is not None
```

The file endpoint may return:
- plain text/JSON content in `result`
- binary content in `content`
- additional response details in `raw`

### File pseudonymization

Use `PseudonymizeFileRequest` for file uploads that should return
pseudonymized content and metadata.

```python
from sap_cloud_sdk.core.data_anonymization import (
    create_client,
    PseudonymizeFileRequest,
)

client = create_client()

request = PseudonymizeFileRequest(
    file_path="sample.json",
    pseudonymization_secret="12345678901234567890123456789012",
)

result = client.pseudonymize_file(request)

if result.content is not None:
    with open(result.filename or "result.zip", "wb") as fp:
        fp.write(result.content)
```

Typical file pseudonymization responses:
- ZIP/binary payload in `content`
- textual response in `result`
- additional response details in `raw`

## Result objects

### `AnonymizeResult`

| Field    | Type   | Description |
|----------|--------|-------------|
| `result` | `str`  | The anonymized text. |
| `raw`    | `dict` | Full raw response from the service (for forward-compatibility). |

### `PseudonymizeResult`

| Field      | Type                  | Description |
|------------|-----------------------|-------------|
| `result`   | `str`                 | The pseudonymized text. |
| `metadata` | `list[EntityMapping]` | Per-entity original ↔ token mappings. |
| `raw`      | `dict`                | Full raw response from the service. |

### `EntityMapping`

| Field         | Type  | Description |
|---------------|-------|-------------|
| `original`    | `str` | The original PII value that was detected. |
| `pseudonym`   | `str` | The token that replaced it. |
| `entity_type` | `str` | PII category (e.g. `"PERSON"`, `"EMAIL"`, `"PHONE"`). |

### `FileOperationResult`

| Field          | Type             | Description |
|----------------|------------------|-------------|
| `result`       | `str \| None`    | Text result when the service returns text or JSON. |
| `content`      | `bytes \| None`  | Raw binary payload, for example a ZIP file. |
| `content_type` | `str`            | Response content type returned by the service. |
| `filename`     | `str \| None`    | Filename from the `Content-Disposition` header, if present. |
| `raw`          | `dict`           | Parsed JSON payload when available and suitable for response inspection. |

## Error Handling

Always catch `DataAnonymizationError` or its subclasses around calls:

```python
from sap_cloud_sdk.core.data_anonymization import (
    create_client,
    AnonymizeTextRequest,
    DataAnonymizationError,
    TransportError,
    AuthenticationError,
)

client = create_client()

try:
    result = client.anonymize_text(
        AnonymizeTextRequest(text="Jane Doe, jane@example.com")
    )
except AuthenticationError as e:
    # mTLS handshake failed — check certificate values or Destination config
    handle_error(e)
except TransportError as e:
    # HTTP call to the service failed — transient issue, safe to retry
    handle_error(e)
except DataAnonymizationError as e:
    # Catch-all for any other SDK error
    handle_error(e)
```

Anonymization failures should generally **not** block business logic. Handle the error without persisting sensitive request or response content.

## Context Manager

`DataAnonymizationClient` supports the context-manager protocol, which ensures transport resources (temp cert files, HTTP sessions) are released when the block exits:

```python
from sap_cloud_sdk.core.data_anonymization import create_client, AnonymizeTextRequest

with create_client() as client:
    result = client.anonymize_text(AnonymizeTextRequest(text="John Doe"))
    assert result.result is not None
# session and any temp certificate files are cleaned up here
```

## Environment Configuration

In a BTP / App Foundation cloud deployment the factory reads credentials from the secret resolver using:

- **Mount path**: `/etc/secrets/appfnd`
- **Env var fallback**: `CLOUD_SDK_CFG`
- **Service name**: `data-anonymization`
- **Instance**: `default` (override with the `instance` parameter of `create_client()`)

The binding JSON is expected to carry a `url` key (the service base URL) and either `cert` + `key` keys (inline Key Store) or a `destination_name` key (BTP Destination Key Store).

For Destination-backed Key Stores, the resolved destination should expose a `KeyStoreLocation` property pointing to a certificate entry in the Destination service. That certificate entry should contain a combined PEM bundle with the private key and certificate chain.

For local development pass an explicit `DataAnonymizationConfig` with inline `cert` / `key` values to `create_client()`.
