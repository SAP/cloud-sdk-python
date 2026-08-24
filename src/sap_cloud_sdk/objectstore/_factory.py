"""Object store client factory — provider detection and dispatch."""

from typing import Any, Union

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

_CLIENTS: dict[ObjectStoreProvider, Any] = {
    ObjectStoreProvider.S3: S3Client,
    ObjectStoreProvider.AZURE: AzureClient,
    ObjectStoreProvider.GCS: GcsClient,
}


def create_client(
    instance: str,
    *,
    config: Union[S3BindingData, AzureBindingData, GcsBindingData, None] = None,
) -> ObjectStoreClient:
    """Create an object store client with automatic provider detection.

    When ``config`` is omitted the function reads the service binding for
    ``instance`` from the secret mount or environment variables, infers the
    cloud provider, and returns the matching concrete client.

    When ``config`` is supplied, provider detection is skipped and the matching
    client is constructed directly from the given credentials.

    Args:
        instance: Instance name used for secret resolution. Must be non-empty.
        config: Optional explicit credentials. If provided, auto-detection is
            skipped.  Pass an ``S3BindingData`` for S3, an
            ``AzureBindingData`` for Azure, or a ``GcsBindingData`` for GCS.

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

    # Auto-detection path.
    keys = read_binding_keys(instance)
    try:
        provider = detect_provider(keys)
    except ValueError as e:
        raise ClientCreationError(
            f"Cannot create objectstore client for instance '{instance}': {e}"
        ) from e

    binding = load_from_env_or_mount(provider, instance)
    return _CLIENTS[provider](binding)
