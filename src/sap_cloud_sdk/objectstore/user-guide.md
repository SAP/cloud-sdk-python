# ObjectStore User Guide

Provides a simple and unified way to connect to Object Store services on SAP BTP. It abstracts configuration, authentication, and transport, making it easy to upload and download files without dealing with provider-specific details.

**Supported providers:** Amazon S3 (and S3-compatible services like MinIO), Azure Blob Storage, and Google Cloud Storage.

## Installation

```bash
# Using uv (recommended)
uv add sap-cloud-sdk

# Using pip
pip install sap-cloud-sdk
```

See further information about installation in the [main documentation](/README.md#installation).

## Import

```python
from sap_cloud_sdk.objectstore import ObjectStoreClient, create_client
```

---

## Getting Started

Use `create_client()` with the logical instance name from your Cloud descriptor.
When no configuration is supplied, it reads the binding, detects S3, Azure, or
GCS from its keys, and creates the matching client.

```python
from sap_cloud_sdk.objectstore import create_client

client = create_client("my-instance")
```

> **`instance` refers to the instance name defined in your Cloud descriptor.**
> It determines the credentials or mounted secrets that are resolved.

### Explicit Configuration

Pass a public configuration type to bypass service-binding discovery:

```python
from sap_cloud_sdk.objectstore import S3Config, create_client

client = create_client(
    "local-minio",
    config=S3Config(
        access_key_id="...",
        secret_access_key="...",
        bucket="my-bucket",
        host="localhost:9000",
        disable_ssl=True,  # Plain HTTP; (default is False)
    ),
)
```

For Azure Blob Storage and GCS, pass `AzureConfig` or `GcsConfig` respectively:

```python
from sap_cloud_sdk.objectstore import AzureConfig, GcsConfig, create_client

azure_client = create_client(
    "azure-store",
    config=AzureConfig(
        container_name="my-container",
        container_uri="https://my-account.blob.core.windows.net/my-container",
        sas_token="...",
    ),
)

gcs_client = create_client(
    "gcs-store",
    config=GcsConfig(
        base64_encoded_private_key_data="...",
        project_id="my-project",
        bucket="my-bucket",
    ),
)
```

---

## Uploading Objects

### From Bytes

```python
data = b"Hello, World!"
client.put_object_from_bytes(name="hello.txt", data=data, content_type="text/plain")
```

### From File

```python
client.put_object_from_file(
    name="document.pdf",
    file_path="/path/to/local/document.pdf",
    content_type="application/pdf",
)
```

### From Stream

```python
import io
import os

stream = io.BytesIO(b"Streamed content")
client.put_object(
    name="stream.txt",
    stream=stream,
    size=len(b"Streamed content"),
    content_type="text/plain",
)

with open("/path/to/file.txt", "rb") as file:
    client.put_object(
        name="uploaded.txt",
        stream=file,
        size=os.path.getsize("/path/to/file.txt"),
        content_type="text/plain",
    )
```

---

## Retrieving and Inspecting Objects

### Get Object Content

`get_object()` returns an `ObjectReader`. Its `read()`, `read(size)`, `close()`,
and context-manager operations are portable across all supported providers.

```python
with client.get_object("hello.txt") as response:
    content = response.read()
    text_content = content.decode("utf-8")
```

You can close a reader explicitly when a context manager is not practical:

```python
response = client.get_object("hello.txt")
try:
    content = response.read()
finally:
    response.close()
```

### Check Object Existence

```python
if client.object_exists("hello.txt"):
    print("File exists!")
else:
    print("File not found")
```

### Get Object Metadata

```python
metadata = client.head_object("hello.txt")

print(f"Key: {metadata.key}")
print(f"Size: {metadata.size} bytes")
print(f"ETag: {metadata.etag}")
print(f"Last Modified: {metadata.last_modified}")
print(f"Content Type: {metadata.content_type}")
```

### List Objects

```python
# An empty prefix lists all objects.
all_objects = client.list_objects(prefix="")

documents = client.list_objects(prefix="documents/")
for obj in documents:
    print(f"{obj.key} - {obj.size} bytes - {obj.last_modified}")
```

---

## Deleting Objects

```python
client.delete_object("hello.txt")

# Deletion is idempotent: no error if the object does not exist.
client.delete_object("non-existent.txt")
```

---

## Multi-tenancy

- **Supported:** No (Object Store is not multi-tenant aware)
- **Authentication:** N/A
- **How to use:** Object Store uses static access-key or provider service
  credentials. Each service binding is scoped to one storage container or bucket.
  To serve multiple tenants, provision a separate service instance per tenant.
- **Further reading:**
  [SAP Object Store Service — SAP Help Portal](https://help.sap.com/docs/object-store)

## Error Handling

The module exposes specific exceptions for configuration, client creation, and
object operations.

```python
from sap_cloud_sdk.objectstore import (
    ClientCreationError,
    ConfigError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)

try:
    with client.get_object("missing-file.txt") as response:
        content = response.read()
except ObjectNotFoundError:
    print("File not found")
except ObjectOperationError as error:
    print(f"Operation failed: {error}")

try:
    client = create_client("my-instance")
except ConfigError as error:
    print(f"Invalid or incomplete binding: {error}")
except ClientCreationError as error:
    print(f"Could not detect or create a client: {error}")

try:
    objects = client.list_objects(prefix="folder/")
except ListObjectsError as error:
    print(f"Failed to list objects: {error}")
```

---

## Configuration

### Provider Detection and Binding Discovery

With no explicit `config`, `create_client()` detects the provider from binding
keys. Detection is case-insensitive. Binding values are loaded in this order:

1. When `SERVICE_BINDING_ROOT` is set, the servicebinding.io flat path:
   `$SERVICE_BINDING_ROOT/objectstore/<field>`.
2. The legacy instance path: `$SERVICE_BINDING_ROOT/objectstore/{instance}/<field>`
   (or `/etc/secrets/appfnd/objectstore/{instance}/<field>` when
   `SERVICE_BINDING_ROOT` is unset).
3. Environment variables named
   `CLOUD_SDK_CFG_OBJECTSTORE_{INSTANCE}_{FIELD}`, with the instance and field
   uppercased and hyphens in the instance replaced by underscores.

See the [Secret Resolver guide](../core/secret_resolver/user-guide.md) for the
general mounting conventions.

### Amazon S3 Configuration

**Required binding keys (mounted files or env vars):**
- `access_key_id` — S3 access key ID
- `secret_access_key` — S3 secret access key
- `bucket` — Bucket name
- `host` — S3-compatible endpoint (e.g. `s3.eu-central-1.amazonaws.com`)

**Environment variables** for instance `my-instance`:

```bash
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_ACCESS_KEY_ID="your-access-key"
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_SECRET_ACCESS_KEY="your-secret-key"
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_BUCKET="your-bucket-name"
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_HOST="s3.eu-central-1.amazonaws.com"
```

Supported S3 endpoints: `s3.{region}.amazonaws.com`, MinIO (`localhost:9000`), or any S3-compatible service.

### Azure Blob Storage Configuration

**Required binding keys (mounted files or env vars):**
- `container_uri` — Full Azure container URI (e.g. `https://{account}.blob.core.windows.net/{container}`)
- `sas_token` — Shared Access Signature (SAS) token
- `container_name` — Azure container name

**Environment variables** for instance `my-instance`:

```bash
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_CONTAINER_URI="https://mystorageaccount.blob.core.windows.net/my-container"
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_SAS_TOKEN="sp=racwdl&st=2024-01-01T00:00:00Z&..."
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_CONTAINER_NAME="my-container"
```

### Google Cloud Storage Configuration

**Required binding keys (mounted files or env vars):**
- `base64EncodedPrivateKeyData` — Base64-encoded service account JSON (camelCase filename for mounted bindings)
- `projectId` — GCP project ID (camelCase filename for mounted bindings)
- `bucket` — Bucket name

**Environment variables** for instance `my-instance`:

```bash
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_BASE64ENCODEDPRIVATEKEYDATA="..."
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_PROJECTID="my-gcp-project"
export CLOUD_SDK_CFG_OBJECTSTORE_MY_INSTANCE_BUCKET="my-bucket"
```
