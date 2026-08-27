"""Azure Blob Storage backend implementation for object store operations."""

import os
from types import TracebackType
from typing import TYPE_CHECKING, BinaryIO, List, NoReturn, Self

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.objectstore.config import AzureConfig
from sap_cloud_sdk.objectstore._models import ObjectMetadata
from sap_cloud_sdk.objectstore._protocol import ObjectReader
from sap_cloud_sdk.objectstore._validation import (
    validate_object_name,
    validate_prefix,
    validate_put_from_bytes,
    validate_put_from_file,
    validate_put_object,
)
from sap_cloud_sdk.objectstore.exceptions import (
    ClientCreationError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)

if TYPE_CHECKING:
    from azure.storage.blob import StorageStreamDownloader


class _AzureObjectReader:
    """Add a managed-reader lifecycle to an Azure blob downloader."""

    def __init__(self, downloader: "StorageStreamDownloader[bytes]") -> None:
        self._downloader: StorageStreamDownloader[bytes] | None = downloader

    def _require_open(self) -> "StorageStreamDownloader[bytes]":
        if self._downloader is None:
            raise ValueError("I/O operation on closed object reader")
        return self._downloader

    def read(self, size: int = -1, /) -> bytes:
        return self._require_open().read(size)

    def close(self) -> None:
        # StorageStreamDownloader has no close operation. Dropping the reference
        # ends the adapter's logical lifetime and releases its buffered state.
        self._downloader = None

    def __enter__(self) -> Self:
        self._require_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        self.close()


class AzureClient:
    """Azure Blob Storage object storage client.

    Provides the standard 8-method object store interface backed by
    Azure Blob Storage. Obtain an instance via ``create_client()``.
    """

    def __init__(self, config: AzureConfig) -> None:
        """Initialise the Azure object storage client.

        Args:
            config: Azure Blob Storage client configuration.

        Raises:
            ClientCreationError: If client initialisation fails.
        """
        try:
            self._container = self._create_container_client(config)
        except ClientCreationError:
            raise
        except Exception as e:
            raise ClientCreationError(f"Failed to initialise AzureClient: {e}") from e

    def _create_container_client(self, cfg: AzureConfig):
        """Build an Azure ContainerClient from binding data.

        Uses the container URI directly (which already includes the container name)
        to construct a ContainerClient — avoids double-appending the container path.
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
            raise ClientCreationError(
                f"Failed to create Azure ContainerClient: {e}"
            ) from e

    def _blob_client(self, name: str):
        """Return a BlobClient for the named blob in this container."""
        return self._container.get_blob_client(name)

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_PUT_OBJECT_FROM_BYTES)
    def put_object_from_bytes(self, name: str, data: bytes, content_type: str) -> None:
        """Upload an object from bytes.

        Args:
            name: Name/key of the object to upload.
            data: Byte data to upload.
            content_type: MIME type of the object.

        Raises:
            ValueError: If any parameter is invalid.
            ObjectOperationError: If the upload fails.
        """
        validate_put_from_bytes(name, data, content_type)

        try:
            from azure.storage.blob import ContentSettings  # lazy

            self._blob_client(name).upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object '{name}': {e}") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_PUT_OBJECT)
    def put_object(
        self, name: str, stream: BinaryIO, size: int, content_type: str
    ) -> None:
        """Upload an object from a stream.

        Args:
            name: Name/key of the object to upload.
            stream: Binary stream containing the object data.
            size: Size of the object in bytes.
            content_type: MIME type of the object.

        Raises:
            ValueError: If any parameter is invalid.
            ObjectOperationError: If the upload fails.
        """
        validate_put_object(name, stream, size, content_type)

        try:
            from azure.storage.blob import ContentSettings  # lazy

            self._blob_client(name).upload_blob(
                stream,
                length=size,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object '{name}': {e}") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_PUT_OBJECT_FROM_FILE)
    def put_object_from_file(
        self, name: str, file_path: str, content_type: str
    ) -> None:
        """Upload an object from a local file.

        Args:
            name: Name/key of the object to upload.
            file_path: Path to the local file to upload.
            content_type: MIME type of the object.

        Raises:
            ValueError: If any parameter is invalid.
            ObjectOperationError: If the upload fails.
        """
        validate_put_from_file(name, file_path, content_type)

        try:
            from azure.storage.blob import ContentSettings  # lazy

            if not os.path.isfile(file_path):
                raise ObjectOperationError(f"File not found: {file_path}")

            with open(file_path, "rb") as f:
                self._blob_client(name).upload_blob(
                    f,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                )
        except ObjectOperationError:
            raise
        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object '{name}': {e}") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_GET_OBJECT)
    def get_object(self, name: str) -> ObjectReader:
        """Download an object as a stream.

        Args:
            name: Name/key of the object to download.

        Returns:
            A readable binary stream of the object data.

        Raises:
            ValueError: If name is invalid.
            ObjectNotFoundError: If the object does not exist.
            ObjectOperationError: If the download fails.
        """
        validate_object_name(name)

        try:
            downloader = self._blob_client(name).download_blob()
            return _AzureObjectReader(downloader)
        except Exception as e:
            self._map_azure_error(e, name, "download")

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_DELETE_OBJECT)
    def delete_object(self, name: str) -> None:
        """Delete an object (idempotent — no error if already absent).

        Args:
            name: Name/key of the object to delete.

        Raises:
            ValueError: If name is invalid.
            ObjectOperationError: If the deletion fails.
        """
        validate_object_name(name)

        try:
            self._blob_client(name).delete_blob()
        except Exception as e:
            try:
                from azure.core.exceptions import ResourceNotFoundError  # lazy

                if isinstance(e, ResourceNotFoundError):
                    return  # idempotent
            except ImportError:
                pass
            raise ObjectOperationError(f"Failed to delete object '{name}': {e}") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_LIST_OBJECTS)
    def list_objects(self, prefix: str) -> List[ObjectMetadata]:
        """List objects with a given prefix.

        Args:
            prefix: Prefix to filter objects by name.

        Returns:
            List of object metadata.

        Raises:
            ValueError: If prefix is invalid.
            ListObjectsError: If listing fails.
        """
        validate_prefix(prefix)

        try:
            result = []
            for blob in self._container.list_blobs(name_starts_with=prefix):
                result.append(
                    ObjectMetadata(
                        key=blob.name,
                        last_modified=blob.last_modified,
                        etag=(blob.etag or "").strip('"'),
                        size=blob.size or 0,
                        storage_class=str(blob.blob_tier) if blob.blob_tier else None,
                        owner=None,
                    )
                )
            return result
        except Exception as e:
            raise ListObjectsError(
                f"Failed to list objects with prefix '{prefix}': {e}"
            ) from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_HEAD_OBJECT)
    def head_object(self, name: str) -> ObjectMetadata:
        """Get metadata for an object without downloading it.

        Args:
            name: Name/key of the object.

        Returns:
            Object metadata.

        Raises:
            ValueError: If name is invalid.
            ObjectNotFoundError: If the object does not exist.
            ObjectOperationError: If the operation fails.
        """
        validate_object_name(name)

        try:
            props = self._blob_client(name).get_blob_properties()
            return ObjectMetadata(
                key=name,
                last_modified=props.last_modified,
                etag=(props.etag or "").strip('"'),
                size=props.size or 0,
                storage_class=str(props.blob_tier) if props.blob_tier else None,
                owner=None,
            )
        except Exception as e:
            self._map_azure_error(e, name, "head")

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_OBJECT_EXISTS)
    def object_exists(self, name: str) -> bool:
        """Check if an object exists.

        Args:
            name: Name/key of the object to check.

        Returns:
            True if the object exists, False otherwise.

        Raises:
            ValueError: If name is invalid.
            ObjectOperationError: If the check fails.
        """
        validate_object_name(name)

        try:
            self.head_object(name)
            return True
        except ObjectNotFoundError:
            return False
        except Exception as e:
            raise ObjectOperationError(
                f"Failed to check if object '{name}' exists: {e}"
            ) from e

    def _map_azure_error(self, exc: Exception, name: str, operation: str) -> NoReturn:
        """Map Azure SDK exceptions to objectstore exceptions and re-raise."""
        try:
            from azure.core.exceptions import (
                HttpResponseError,
                ResourceNotFoundError,
            )  # lazy

            if isinstance(exc, ResourceNotFoundError) or (
                isinstance(exc, HttpResponseError) and exc.status_code == 404
            ):
                raise ObjectNotFoundError(f"Object '{name}' not found") from exc
        except ImportError:
            pass
        raise ObjectOperationError(
            f"Failed to {operation} object '{name}': {exc}"
        ) from exc
