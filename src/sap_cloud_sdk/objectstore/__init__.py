"""SAP Cloud SDK for Python - Object Store module

``create_client()`` auto-detects the cloud provider from the service binding and
returns a client implementing the ``ObjectStoreClient`` protocol. Supported
providers: S3/MinIO, Azure Blob Storage, Google Cloud Storage.

Usage:
    from sap_cloud_sdk.objectstore import create_client

    client = create_client("object-store-1")
"""

from sap_cloud_sdk.objectstore._factory import create_client
from sap_cloud_sdk.objectstore._models import (
    AzureBindingData,
    GcsBindingData,
    ObjectMetadata,
    S3BindingData,
)
from sap_cloud_sdk.objectstore._protocol import ObjectStoreClient
from sap_cloud_sdk.objectstore.exceptions import (
    ClientCreationError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
    ObjectStoreError,
)

__all__ = [
    # Protocol (usable as a type annotation)
    "ObjectStoreClient",
    # Binding data types (for explicit config= usage)
    "S3BindingData",
    "AzureBindingData",
    "GcsBindingData",
    # Metadata model
    "ObjectMetadata",
    # Factory function
    "create_client",
    # Exceptions
    "ObjectStoreError",
    "ClientCreationError",
    "ObjectOperationError",
    "ObjectNotFoundError",
    "ListObjectsError",
]
