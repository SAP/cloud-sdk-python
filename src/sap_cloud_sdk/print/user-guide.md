# Print Service User Guide

This module provides a Python SDK for interacting with the SAP Print Service. It supports managing print queues, uploading documents, and creating print tasks.

## Installation

```bash
# Using pip
pip install sap-cloud-sdk
```

See further information about installation in the [main documentation](/README.md#installation).

## Import

```python
from sap_cloud_sdk.print import create_client
from sap_cloud_sdk.print import (
    PrintQueue, PrintProfile, PrintContent, PrintTask, PrintTaskMetadata,
)
from sap_cloud_sdk.print.exceptions import (
    ClientCreationError, ConfigError, PrintOperationError, HttpError,
)
```

---

## Getting Started

Use `create_client()` to get a client with automatic configuration detection:

```python
from sap_cloud_sdk.print import create_client

# Load credentials from mounted secrets or environment variables
client = create_client(instance="my-instance")
```

You can also provide credentials directly:

```python
from sap_cloud_sdk.print import create_client
from sap_cloud_sdk.print.config import PrintConfig

config = PrintConfig(
    url="https://api.eu10.print.services.sap",
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://your-subdomain.authentication.eu10.hana.ondemand.com/oauth/token",
)

client = create_client(config=config)
```

> **`instance` refers to the instance name defined in your Cloud descriptor.**
>
> This name determines which set of credentials or mounted secrets to resolve from the environment.

---

## Queue Management

### List All Queues

```python
queues = client.list_queues()

for queue in queues:
    print(f"{queue.qname} — {queue.qdescription}")
    print(f"  Format: {queue.qformat} ({queue.qformat_descript})")
    print(f"  Location: {queue.location_id}")
```

### Create a Queue

```python
from sap_cloud_sdk.print import PrintQueue

queue = PrintQueue(
    qname="my-queue",
    qdescription="Main invoice printer",
    qformat="acrobat6.xdc",
    tech_user_name="tech_user",
    cleanup_prd=1,
)

client.create_queue(queue)
```
> **Note:** `tech_user` should be created firstly, please check the [official help guide]('https://help.sap.com/docs/SCP_PRINT_SERVICE/7615de0949ce441d8bc5df7725a6bfc6/b497cdaba35946e9a871bc098e881b69.html').

The queue `qname` must be unique and contain only A–Z, a–z, 0–9, underscores, or hyphens (max 32 characters).

### Get Print Profiles

Returns the print profiles defined for a queue. Use `profile_name` values when creating print tasks to pass profile parameters directly to the physical printer.

```python
profiles = client.get_print_profiles("my-queue")

for profile in profiles:
    print(f"{profile.profile_name} — status={profile.profile_status}")
```

---

## Document Upload

### Upload a Document

Uploads a document to Print Service cloud storage and returns a document ID (UUID). This ID is used as the `object_key` in `PrintContent` and as the `item_id` in `PrintTask`.

```python
# From a file on disk
with open("invoice.pdf", "rb") as f:
    doc_id = client.upload_document(f, filename="invoice.pdf")

print(f"Uploaded document ID: {doc_id}")
```

```python
# From in-memory bytes
import io

content = io.BytesIO(b"%PDF-1.4 ...")
doc_id = client.upload_document(content, filename="invoice.pdf")
```

Set `scan=False` to skip virus scanning:

```python
doc_id = client.upload_document(f, filename="invoice.pdf", scan=False)
```

---

## Print Tasks

### Create a Print Task

Sends a print job to a queue. The `task.item_id` must match the `object_key` of one entry in `task.print_contents` — that entry becomes the main document.

```python
from sap_cloud_sdk.print import PrintContent, PrintTask

task = PrintTask(
    item_id=doc_id,
    qname="my-queue",
    print_contents=[PrintContent(object_key=doc_id, document_name="invoice.pdf")],
)

client.create_print_task(task)
```

### Print with Multiple Documents

Additional entries in `print_contents` are treated as attachments and must have filenames that include the extension (e.g., `attachment.pdf`).

```python
with open("main.pdf", "rb") as f:
    main_id = client.upload_document(f, filename="main.pdf")

with open("attachment.pdf", "rb") as f:
    att_id = client.upload_document(f, filename="attachment.pdf")

task = PrintTask(
    item_id=main_id,
    qname="my-queue",
    number_of_copies=2,
    username="user@example.com",
    print_contents=[
        PrintContent(object_key=main_id, document_name="main.pdf"),
        PrintContent(object_key=att_id, document_name="attachment.pdf"),
    ],
)

client.create_print_task(task)
```

### Using a Print Profile

```python
profiles = client.get_print_profiles("my-queue")
profile_name = profiles[0].profile_name  # e.g., "Defaults"

task = PrintTask(
    item_id=doc_id,
    qname="my-queue",
    print_contents=[PrintContent(object_key=doc_id, document_name="doc.pdf")],
    profile_name=profile_name,
)

client.create_print_task(task)
```

### Print Task with Metadata

```python
from sap_cloud_sdk.print import PrintTaskMetadata

task = PrintTask(
    item_id=doc_id,
    qname="my-queue",
    print_contents=[PrintContent(object_key=doc_id, document_name="doc.pdf")],
    metadata=PrintTaskMetadata(
        version=1.0,
        business_user="user@example.com",
        object_node_type="INVOICE",
    ),
)

client.create_print_task(task)
```

---

## Error Handling

The Print module provides specific exceptions for different error scenarios:

```python
from sap_cloud_sdk.print.exceptions import (
    ClientCreationError,
    ConfigError,
    PrintOperationError,
    HttpError,
)

try:
    client = create_client()
    queues = client.list_queues()
except ClientCreationError as e:
    print(f"Could not connect to Print Service: {e}")
except ConfigError as e:
    print(f"Configuration error: {e}")
except PrintOperationError as e:
    print(f"Operation failed: {e}")
except HttpError as e:
    print(f"HTTP error ({e.status_code}): {e.response_text}")
```

### Exception Hierarchy

| Exception | Description |
|---|---|
| `ClientCreationError` | Client creation fails (bad config, missing credentials) |
| `ConfigError` | Secret resolution or config parsing fails |
| `PrintOperationError` | An API operation fails (wraps `HttpError`) |
| `HttpError` | Raw HTTP error with `status_code` and `response_text` |

---

## Models

### Queue Models

- **`PrintQueue`**: Print queue — `qname` (required), `qdescription`, `qformat`, `qformat_descript`, `cleanup_prd` (1–7 days), `tech_user_name`, `location_id`, `location_id_type`, `creator`
- **`PrintProfile`**: Queue print profile — `queue_name`, `profile_name`, `profile_params`, `profile_status`

### Task Models

- **`PrintContent`**: Document reference — `object_key` (document ID from `upload_document()`), `document_name` (attachments must include file extension)
- **`PrintTask`**: Print job — `item_id` (main document's `object_key`), `qname`, `print_contents`, `number_of_copies` (default 1), `username`, `profile_name`, `metadata`
- **`PrintTaskMetadata`**: Optional task metadata — `version` (required when provided), `business_user`, `object_node_type`

---

## Configuration

### Service Binding

- **Mount path**: `$SERVICE_BINDING_ROOT/print/{instance}/` (defaults to `/etc/secrets/appfnd/print/{instance}/`)
- **Required Keys**: `url` (Print Service API base URL), `uaa` (JSON string with XSUAA credentials)
- **Env var fallback**: `CLOUD_SDK_CFG_PRINT_{INSTANCE}_{FIELD}` (uppercased, hyphens in instance replaced with `_`)

> **Note:** `SERVICE_BINDING_ROOT` defaults to `/etc/secrets/appfnd` when not set. See the [Secret Resolver guide](../core/secret_resolver/user-guide.md) for details.

#### Mounted Secrets (Kubernetes)

```
$SERVICE_BINDING_ROOT/print/{instance}/
├── url
└── uaa
```

#### Environment Variables

```bash
# Example for Print Service with instance name "default"
export CLOUD_SDK_CFG_PRINT_DEFAULT_URL="https://api.eu10.print.services.sap"
export CLOUD_SDK_CFG_PRINT_DEFAULT_UAA='{"clientid":"...","clientsecret":"...","url":"https://subdomain.authentication.eu10.hana.ondemand.com"}'
```

#### UAA JSON Schema

The `uaa` key must contain a JSON string with the XSUAA credentials:

```json
{
  "clientid": "sb-xxx!bxxx|print!bxxx",
  "clientsecret": "xxx",
  "url": "https://subdomain.authentication.region.hana.ondemand.com"
}
```
