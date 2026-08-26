"""Data models for the object store module."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Optional


class ObjectStoreProvider(StrEnum):
    """Supported object store backend providers."""

    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"


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
