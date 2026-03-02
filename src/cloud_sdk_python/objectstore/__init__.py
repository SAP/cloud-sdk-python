"""SAP Cloud SDK for Python - Object Store module

The create_client() uses secret resolver to load credentials from mounts/env vars

Usage:
    from cloud_sdk_python.objectstore import create_client

    client = create_client("object-store-1")
"""

import os
from typing import Optional

from cloud_sdk_python.objectstore.exceptions import (
    ObjectStoreError,
    ClientCreationError,
    ObjectOperationError,
    ObjectNotFoundError,
    ListObjectsError,
)
from cloud_sdk_python.objectstore._models import ObjectStoreBindingData, ObjectMetadata
from cloud_sdk_python.objectstore._s3 import ObjectStoreClient
from cloud_sdk_python.core.secret_resolver import read_from_mount_and_fallback_to_env_var


def create_client(
    instance: str,
    *,
    config: Optional[ObjectStoreBindingData] = None,
    disable_ssl: bool = False
) -> ObjectStoreClient:
    """Creates an ObjectStoreClient with automatic local/cloud detection. 
    Uses secret resolver to load credentials from mounted secrets or environment variables
    
    Args:
        instance: Instance name for cloud mode secret resolution. Must be a non-empty string.
        config: Optional explicit configuration. If provided, auto-detection is skipped
                and this configuration is used directly.
        disable_ssl: Whether to disable SSL/TLS connections. Defaults to False.
        
    Returns:
        ObjectStoreClient: Configured client ready for object storage operations.
        
    Raises:
        ValueError: If instance parameter is empty or None.
        ClientCreationError: If client creation fails due to configuration or connection issues.
    """
    if not instance or not instance.strip():
        raise ValueError("instance parameter must be a non-empty string")
    
    # Cloud mode: with explicit configuration
    if config is not None:
        return ObjectStoreClient(config, disable_ssl=disable_ssl)
        
    # Cloud mode: use secret resolver to load configuration
    config = ObjectStoreBindingData()
    read_from_mount_and_fallback_to_env_var(
        base_volume_mount="/etc/secrets/appfnd",
        base_var_name="CLOUD_SDK_CFG",
        module="objectstore",
        instance=instance,
        target=config
    )
    return ObjectStoreClient(config, disable_ssl=disable_ssl)


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
