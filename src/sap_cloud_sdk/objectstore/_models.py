"""Data models for the object store module."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Optional


class ObjectStoreProvider(StrEnum):
    """Supported object store backend providers."""

    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"


@dataclass
class S3BindingData:
    """Configuration data for S3-compatible object storage credentials.

    Contains the necessary connection parameters for S3-compatible object storage.
    Used internally by the SDK and can be provided explicitly to create_client().
    """

    access_key_id: str = ""
    secret_access_key: str = ""
    bucket: str = ""
    host: str = ""


@dataclass
class AzureBindingData:
    """Configuration data for Azure Blob Storage credentials.

    Used internally by the SDK and can be provided explicitly to create_client().
    """

    account_name: str = ""
    container_name: str = ""
    container_uri: str = ""
    region: str = ""
    sas_token: str = ""


@dataclass
class GcsBindingData:
    """Configuration data for Google Cloud Storage credentials.

    camelCase binding keys are aliased via field metadata so the secret
    resolver can map them to Python-friendly attribute names.
    Used internally by the SDK and can be provided explicitly to create_client().
    """

    base64_encoded_private_key_data: str = field(
        default="", metadata={"secret": "base64EncodedPrivateKeyData"}
    )
    project_id: str = field(default="", metadata={"secret": "projectId"})
    key_algo: str = field(default="", metadata={"secret": "keyAlgo"})
    region: str = ""
    bucket: str = ""


@dataclass(frozen=True)
class ObjectMetadata:
    """Metadata information for a stored object.

    Contains metadata about an object in the object store,
    typically returned by list_objects() and head_object() operations.

    Attributes:
        key: Object key/name in the store.
        last_modified: When the object was last modified.
        etag: Entity tag for versioning and integrity checks.
        size: Size of the object in bytes.
        storage_class: Storage class (e.g., STANDARD, GLACIER). Optional.
        owner: Owner of the object. Optional.
    """

    key: str
    last_modified: datetime
    etag: str
    size: int
    storage_class: Optional[str] = None
    owner: Optional[str] = None
