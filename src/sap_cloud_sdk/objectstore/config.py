"""Binding data and client configuration for object store backends."""

from dataclasses import dataclass, field
from typing import Union

from sap_cloud_sdk.core.secret_resolver import read_from_mount_and_fallback_to_env_var
from sap_cloud_sdk.objectstore._models import ObjectStoreProvider
from sap_cloud_sdk.objectstore.exceptions import ConfigError


@dataclass
class S3Config:
    """Client configuration for S3-compatible object storage.

    Args:
        access_key_id: S3 access key.
        secret_access_key: S3 secret key.
        bucket: Target bucket name.
        host: S3-compatible endpoint host.
        disable_ssl: Disable TLS for the MinIO connection. Useful for local
            development against an HTTP-only MinIO instance. Defaults to False.
    """

    access_key_id: str
    secret_access_key: str
    bucket: str
    host: str
    disable_ssl: bool = False


@dataclass
class AzureConfig:
    """Client configuration for Azure Blob Storage.

    Args:
        account_name: Azure storage account name.
        container_name: Container name.
        container_uri: Full container URI.
        region: Azure region.
        sas_token: Shared access signature token.
    """

    account_name: str
    container_name: str
    container_uri: str
    region: str
    sas_token: str


@dataclass
class GcsConfig:
    """Client configuration for Google Cloud Storage.

    Args:
        base64_encoded_private_key_data: Base64-encoded service account JSON.
        project_id: GCP project ID.
        bucket: Target bucket name.
    """

    base64_encoded_private_key_data: str
    project_id: str
    bucket: str


@dataclass
class S3BindingData:
    """Raw service-binding credentials for S3-compatible object storage.

    Filled by the secret resolver; all fields are plain strings.
    """

    access_key_id: str = ""
    secret_access_key: str = ""
    bucket: str = ""
    host: str = ""

    def validate(self) -> None:
        """Raise ConfigError if any runtime-required field is empty."""
        missing = [
            name
            for name, value in [
                ("access_key_id", self.access_key_id),
                ("secret_access_key", self.secret_access_key),
                ("bucket", self.bucket),
                ("host", self.host),
            ]
            if not value
        ]
        if missing:
            raise ConfigError(
                f"s3 binding is missing required field(s): {', '.join(missing)}"
            )

    def to_config(self, *, disable_ssl: bool = False) -> S3Config:
        """Return an S3Config with credentials from this binding."""
        return S3Config(
            access_key_id=self.access_key_id,
            secret_access_key=self.secret_access_key,
            bucket=self.bucket,
            host=self.host,
            disable_ssl=disable_ssl,
        )


@dataclass
class AzureBindingData:
    """Raw service-binding credentials for Azure Blob Storage.

    Filled by the secret resolver; all fields are plain strings.
    """

    account_name: str = ""
    container_name: str = ""
    container_uri: str = ""
    region: str = ""
    sas_token: str = ""

    def validate(self) -> None:
        """Raise ConfigError if any runtime-required field is empty."""
        missing = [
            name
            for name, value in [
                ("container_uri", self.container_uri),
                ("sas_token", self.sas_token),
            ]
            if not value
        ]
        if missing:
            raise ConfigError(
                f"azure binding is missing required field(s): {', '.join(missing)}"
            )

    def to_config(self) -> AzureConfig:
        """Return an AzureConfig with credentials from this binding."""
        return AzureConfig(
            account_name=self.account_name,
            container_name=self.container_name,
            container_uri=self.container_uri,
            region=self.region,
            sas_token=self.sas_token,
        )


@dataclass
class GcsBindingData:
    """Raw service-binding credentials for Google Cloud Storage.

    Filled by the secret resolver; all fields are plain strings.
    """

    base64EncodedPrivateKeyData: str = field(
        default="", metadata={"secret": "base64EncodedPrivateKeyData"}
    )
    projectId: str = field(default="", metadata={"secret": "projectId"})
    bucket: str = ""
    key_algo: str = ""
    region: str = ""

    def validate(self) -> None:
        """Raise ConfigError if any runtime-required field is empty."""
        missing = [
            name
            for name, value in [
                ("base64EncodedPrivateKeyData", self.base64EncodedPrivateKeyData),
                ("projectId", self.projectId),
                ("bucket", self.bucket),
            ]
            if not value
        ]
        if missing:
            raise ConfigError(
                f"gcs binding is missing required field(s): {', '.join(missing)}"
            )

    def to_config(self) -> GcsConfig:
        """Return a GcsConfig with credentials from this binding."""
        return GcsConfig(
            base64_encoded_private_key_data=self.base64EncodedPrivateKeyData,
            project_id=self.projectId,
            bucket=self.bucket,
        )


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
) -> Union[S3Config, AzureConfig, GcsConfig]:
    """Resolve, validate, and wrap the binding for a detected provider.

    Args:
        provider: The provider detected for this instance.
        instance: Logical instance name used for secret resolution.

    Returns:
        The validated config for ``provider``.

    Raises:
        ConfigError: If loading or validation fails.
    """
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
        raise ConfigError(
            f"failed to load objectstore configuration for instance='{instance}': {e}"
        ) from e
    binding.validate()
    return binding.to_config()
