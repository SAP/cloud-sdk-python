# ObjectStore User Guide

This module provides a simple API for interacting with S3-compatible object storage.

Provides a simple and unified way to connect to Object Store services. It abstracts configuration, authentication, and transport, making it easy to upload and download files without dealing with provider-specific details.

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
from sap_cloud_sdk.objectstore import create_client, ObjectStoreClient
from sap_cloud_sdk.objectstore import ObjectStoreBindingData
```

---

## Getting Started

Use `create_client()` to get a client with automatic configuration detection:

```python
from sap_cloud_sdk.objectstore import create_client

# Automatically detects local vs cloud mode
client = create_client("my-instance")
```

You can also specify additional parameters if needed:

```python
from sap_cloud_sdk.objectstore import create_client

# Custom configuration with SSL disabled
client = create_client(
    "my-instance",
    disable_ssl=True  # Disable SSL (default is False)
)
```

> **`instance` refers to the instance name defined in your Cloud descriptor.**
>
> This name determines which set of credentials or mounted secrets to resolve from the environment.

---

## Uploading Objects

### From Bytes

```python
# Upload binary data directly
data = b"Hello, World!"
client.put_object_from_bytes(
    name="hello.txt",
    data=data,
    content_type="text/plain"
)
```

### From File

```python
# Upload from a local file
client.put_object_from_file(
    name="document.pdf",
    file_path="/path/to/local/document.pdf",
    content_type="application/pdf"
)
```

### From Stream

```python
import io

# Upload from a stream/file-like object
stream = io.BytesIO(b"Streamed content")
client.put_object(
    name="stream.txt",
    stream=stream,
    size=len(b"Streamed content"),
    content_type="text/plain"
)

# Or with a real file object
with open("/path/to/file.txt", "rb") as f:
    # Get file size
    import os
    size = os.path.getsize("/path/to/file.txt")

    client.put_object(
        name="uploaded.txt",
        stream=f,
        size=size,
        content_type="text/plain"
    )
```

---

## Retrieving and Inspecting Objects

### Get Object Content

```python
# Download an object
response = client.get_object("hello.txt")

# Read the content
content = response.read()  # Returns bytes
text_content = content.decode('utf-8')  # Convert to string if needed

# Don't forget to close the response
response.close()

# Or use as context manager (automatically closes)
with client.get_object("hello.txt") as response:
    content = response.read()
```

### Check Object Existence

```python
# Check if an object exists
if client.object_exists("hello.txt"):
    print("File exists!")
else:
    print("File not found")
```

### Get Object Metadata

```python
# Get object metadata without downloading content
metadata = client.head_object("hello.txt")

print(f"Key: {metadata.key}")
print(f"Size: {metadata.size} bytes")
print(f"ETag: {metadata.etag}")
print(f"Last Modified: {metadata.last_modified}")
print(f"Content Type: {metadata.content_type}")
```

### List Objects

```python
# List all objects
all_objects = client.list_objects()

# List objects with a prefix
documents = client.list_objects(prefix="documents/")

# Process the results
for obj in documents:
    print(f"{obj.key} - {obj.size} bytes - {obj.last_modified}")
```

---

## Deleting Objects

```python
# Delete a single object
client.delete_object("hello.txt")

# Delete operation is idempotent - no error if object doesn't exist
client.delete_object("non-existent.txt")  # This won't raise an error
```

---

## Error Handling

The ObjectStore module provides specific exceptions for different error scenarios:

```python
from sap_cloud_sdk.objectstore import (
    ObjectNotFoundError,
    ObjectOperationError,
    ClientCreationError,
    ListObjectsError
)

try:
    content = client.get_object("missing-file.txt")
except ObjectNotFoundError:
    print("File not found")
except ObjectOperationError as e:
    print(f"Operation failed: {e}")

try:
    client.put_object_from_bytes("test.txt", b"data", "text/plain")
except ObjectOperationError as e:
    print(f"Upload failed: {e}")

try:
    objects = client.list_objects("folder/")
except ListObjectsError as e:
    print(f"Failed to list objects: {e}")
```

---

## Configuration

### Service Binding

- **Mount path**: `$SERVICE_BINDING_ROOT/objectstore/{instance}/` (defaults to `/etc/secrets/appfnd/objectstore/{instance}/`)
- **Required Keys**: `access_key_id`, `secret_access_key`, `bucket`, `host`
- **Env var fallback**: `CLOUD_SDK_CFG_OBJECTSTORE_{INSTANCE}_{FIELD}` (uppercased, hyphens in instance replaced with `_`)

> **Note:** `SERVICE_BINDING_ROOT` defaults to `/etc/secrets/appfnd` when not set. See the [Secret Resolver guide](../core/secret_resolver/user-guide.md) for details.

#### Mounted Secrets (Kubernetes)

```
$SERVICE_BINDING_ROOT/objectstore/{instance}/
├── access_key_id
├── secret_access_key
├── bucket
└── host
```

#### Environment Variables

```bash
# Example for ObjectStore with instance name "credentials"
export CLOUD_SDK_CFG_OBJECTSTORE_CREDENTIALS_ACCESS_KEY_ID="your-access-key"
export CLOUD_SDK_CFG_OBJECTSTORE_CREDENTIALS_SECRET_ACCESS_KEY="your-secret-key"
export CLOUD_SDK_CFG_OBJECTSTORE_CREDENTIALS_BUCKET="your-bucket-name"
export CLOUD_SDK_CFG_OBJECTSTORE_CREDENTIALS_HOST="s3.amazonaws.com"
```
