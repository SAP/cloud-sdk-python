"""SAP Cloud SDK for Python - Object Store module

The create_client() uses ConfigFactory to load credentials from mounts/env vars
with proactive rotation detection via mtime tracking.

Usage:
    from sap_cloud_sdk.objectstore import create_client

    client = create_client("object-store-1")
"""

from typing import Optional

from sap_cloud_sdk.objectstore.exceptions import (
    ObjectStoreError,
    ClientCreationError,
    ObjectOperationError,
    ObjectNotFoundError,
    ListObjectsError,
)
from sap_cloud_sdk.objectstore._models import ObjectStoreBindingData, ObjectMetadata
from sap_cloud_sdk.objectstore._s3 import ObjectStoreClient


def _make_static_factory(config: ObjectStoreBindingData):
    """Wrap a fixed config in a no-op factory (no rotation tracking)."""

    def _factory() -> ObjectStoreBindingData:
        return config

    return _factory


def create_client(
    instance: str,
    *,
    config: Optional[ObjectStoreBindingData] = None,
    disable_ssl: bool = False,
) -> ObjectStoreClient:
    """Create an ObjectStoreClient with automatic credential detection.

    Credentials are loaded from a mounted volume or environment variables and
    tracked for secret rotation via :class:`~sap_cloud_sdk.core.secret_resolver.ConfigFactory`.

    Args:
        instance: Instance name for secret resolution. Must be a non-empty string.
        config: Optional explicit configuration. When provided, binding
                discovery is skipped and rotation tracking is disabled.
        disable_ssl: Whether to disable SSL/TLS connections. Defaults to False.

    Returns:
        ObjectStoreClient: Configured client ready for object storage operations.

    Raises:
        ValueError: If instance parameter is empty or None.
        ClientCreationError: If client creation fails due to configuration or connection issues.
    """
    if not instance or not instance.strip():
        raise ValueError("instance parameter must be a non-empty string")

    if config is not None:
        return ObjectStoreClient(_make_static_factory(config), disable_ssl=disable_ssl)

    from sap_cloud_sdk.core.secret_resolver import ConfigFactory

    factory: ConfigFactory[ObjectStoreBindingData] = ConfigFactory(
        module="objectstore",
        instance=instance,
        binding_cls=ObjectStoreBindingData,
        extract=lambda b: b,
    )
    return ObjectStoreClient(factory, disable_ssl=disable_ssl)


__all__ = [
    # Public user-facing types
    "ObjectMetadata",
    "ObjectStoreBindingData",
    # Factory function
    "create_client",
    # Exceptions
    "ObjectStoreError",
    "ClientCreationError",
    "ObjectOperationError",
    "ObjectNotFoundError",
    "ListObjectsError",
]
