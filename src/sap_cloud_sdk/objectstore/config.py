"""Credential transforms and client builders for object store backends."""

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


def build_azure_container_client(cfg: AzureBindingData):
    """Build an Azure ContainerClient from binding data.

    Uses the container URI directly (which already includes the container name)
    to construct a ContainerClient — avoids double-appending the container path.

    Args:
        cfg: Azure binding credentials.

    Returns:
        Configured ContainerClient instance.

    Raises:
        ClientCreationError: If client initialisation fails.
    """
    try:
        from azure.storage.blob import ContainerClient  # lazy: optional extra

        return ContainerClient.from_container_url(
            cfg.container_uri, credential=cfg.sas_token
        )
    except ImportError as e:
        raise ClientCreationError(
            "azure-storage-blob is required for Azure Object Store support. "
            "Install it with: pip install 'sap-cloud-sdk[azure]'"
        ) from e
    except Exception as e:
        raise ClientCreationError(f"Failed to create Azure ContainerClient: {e}") from e


def build_gcs_client(cfg: GcsBindingData):
    """Build a Google Cloud Storage Client from binding data.

    Decodes the base64-encoded service-account JSON and creates a
    storage.Client using the embedded credentials.

    Args:
        cfg: GCS binding credentials.

    Returns:
        Configured google.cloud.storage.Client instance.

    Raises:
        ClientCreationError: If client initialisation fails.
    """
    try:
        import base64
        import json

        from google.cloud import storage  # lazy: optional extra
        from google.oauth2 import service_account  # lazy: optional extra

        info = json.loads(base64.b64decode(cfg.base64_encoded_private_key_data))
        creds = service_account.Credentials.from_service_account_info(info)
        return storage.Client(project=cfg.project_id, credentials=creds)
    except ImportError as e:
        raise ClientCreationError(
            "google-cloud-storage is required for GCS Object Store support. "
            "Install it with: pip install 'sap-cloud-sdk[gcs]'"
        ) from e
    except Exception as e:
        raise ClientCreationError(f"Failed to create GCS storage client: {e}") from e
