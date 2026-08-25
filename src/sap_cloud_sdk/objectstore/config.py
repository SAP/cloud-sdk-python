"""Credential loading for object store backends."""

from typing import Union

from sap_cloud_sdk.core.secret_resolver import read_from_mount_and_fallback_to_env_var
from sap_cloud_sdk.objectstore._models import (
    AzureBindingData,
    GcsBindingData,
    ObjectStoreProvider,
    S3BindingData,
)
from sap_cloud_sdk.objectstore.exceptions import ClientCreationError

_BINDING_TYPES: dict[
    ObjectStoreProvider,
    type[S3BindingData] | type[AzureBindingData] | type[GcsBindingData],
] = {
    ObjectStoreProvider.S3: S3BindingData,
    ObjectStoreProvider.AZURE: AzureBindingData,
    ObjectStoreProvider.GCS: GcsBindingData,
}


def load_from_env_or_mount(
    provider: ObjectStoreProvider, instance: str
) -> Union[S3BindingData, AzureBindingData, GcsBindingData]:
    """Resolve the typed binding for a detected provider from mount/env."""
    binding = _BINDING_TYPES[provider]()
    try:
        read_from_mount_and_fallback_to_env_var(
            base_volume_mount="/etc/secrets/appfnd",
            base_var_name="CLOUD_SDK_CFG",
            module="objectstore",
            instance=instance,
            target=binding,
        )
    except Exception as e:
        raise ClientCreationError(
            f"failed to load objectstore configuration for instance='{instance}': {e}"
        ) from e
    return binding
