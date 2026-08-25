"""Object store client factory — provider detection and dispatch."""

from typing import Union

from sap_cloud_sdk.objectstore._azure import AzureClient
from sap_cloud_sdk.objectstore._detect import detect_provider, read_binding_keys
from sap_cloud_sdk.objectstore._gcs import GcsClient
from sap_cloud_sdk.objectstore._models import (
    AzureBindingData,
    GcsBindingData,
    ObjectStoreProvider,
    S3BindingData,
)
from sap_cloud_sdk.objectstore._protocol import ObjectStoreClient
from sap_cloud_sdk.objectstore._s3 import S3Client
from sap_cloud_sdk.objectstore.config import load_from_env_or_mount
from sap_cloud_sdk.objectstore.exceptions import ClientCreationError


def create_client(
    instance: str,
    *,
    config: Union[S3BindingData, AzureBindingData, GcsBindingData, None] = None,
) -> ObjectStoreClient:
    """Create an object store client with automatic provider detection.

    When ``config`` is omitted the function reads the service binding for
    ``instance`` from the secret mount or environment variables, infers the
    cloud provider, and returns the matching concrete client.

    Args:
        instance: Instance name used for secret resolution. Must be non-empty.
        config: Optional explicit credentials. If provided, auto-detection is skipped
        and this configuration is used directly.

    Returns:
        A client satisfying the ``ObjectStoreClient`` protocol.

    Raises:
        ValueError: If ``instance`` is empty or None.
        ClientCreationError: If no provider can be detected or client creation
        fails.
    """
    if not instance or not instance.strip():
        raise ValueError("instance parameter must be a non-empty string")

    if config is not None:
        if isinstance(config, S3BindingData):
            return S3Client(config)
        if isinstance(config, AzureBindingData):
            return AzureClient(config)
        if isinstance(config, GcsBindingData):
            return GcsClient(config)
        raise ClientCreationError(
            f"Unsupported config type for explicit client creation: "
            f"{type(config).__name__}"
        )

    keys = read_binding_keys(instance)
    try:
        provider = detect_provider(keys)
    except ValueError as e:
        raise ClientCreationError(
            f"Cannot create objectstore client for instance '{instance}': {e}"
        ) from e

    binding = load_from_env_or_mount(provider, instance)
    if provider is ObjectStoreProvider.S3:
        assert isinstance(binding, S3BindingData)
        return S3Client(binding)
    if provider is ObjectStoreProvider.AZURE:
        assert isinstance(binding, AzureBindingData)
        return AzureClient(binding)
    if provider is ObjectStoreProvider.GCS:
        assert isinstance(binding, GcsBindingData)
        return GcsClient(binding)
    raise ClientCreationError(f"Unsupported provider: {provider}")
