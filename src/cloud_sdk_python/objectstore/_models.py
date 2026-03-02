"""Data models for the object store module."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ObjectStoreBindingData:
    """Configuration data for object store connection credentials.
    
    Contains the necessary connection parameters for S3-compatible object storage.
    Used internally by the SDK and can be provided explicitly to create_client().
    """
    access_key_id: str = ""
    secret_access_key: str = ""
    bucket: str = ""
    host: str = ""


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
