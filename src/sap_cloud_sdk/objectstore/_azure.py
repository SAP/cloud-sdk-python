"""Azure Blob Storage backend implementation for object store operations."""

import os
from typing import IO, BinaryIO, List, NoReturn

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.objectstore._models import AzureBindingData, ObjectMetadata
from sap_cloud_sdk.objectstore._validation import (
    EMPTY_CONTENT_TYPE_ERROR,
    EMPTY_FILE_PATH_ERROR,
    EMPTY_NAME_ERROR,
    INVALID_DATA_TYPE_ERROR,
    INVALID_PREFIX_TYPE_ERROR,
    INVALID_STREAM_ERROR,
    NEGATIVE_SIZE_ERROR,
)
from sap_cloud_sdk.objectstore.config import build_azure_container_client
from sap_cloud_sdk.objectstore.exceptions import (
    ClientCreationError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)


class AzureClient:
    """Azure Blob Storage object storage client.

    Provides the standard 8-method object store interface backed by
    Azure Blob Storage. Obtain an instance via ``create_client()``.
    """

    def __init__(self, creds_config: AzureBindingData) -> None:
        """Initialise the Azure object storage client.

        Args:
            creds_config: Azure Blob Storage credentials.

        Raises:
            ClientCreationError: If client initialisation fails.
        """
        try:
            self._container = build_azure_container_client(creds_config)
        except ClientCreationError:
            raise
        except Exception as e:
            raise ClientCreationError(f"Failed to initialise AzureClient: {e}") from e

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
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)
        if not isinstance(data, bytes):
            raise ValueError(INVALID_DATA_TYPE_ERROR)
        if not content_type:
            raise ValueError(EMPTY_CONTENT_TYPE_ERROR)

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
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)
        if not hasattr(stream, "read"):
            raise ValueError(INVALID_STREAM_ERROR)
        if size < 0:
            raise ValueError(NEGATIVE_SIZE_ERROR)
        if not content_type:
            raise ValueError(EMPTY_CONTENT_TYPE_ERROR)

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
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)
        if not file_path:
            raise ValueError(EMPTY_FILE_PATH_ERROR)
        if not content_type:
            raise ValueError(EMPTY_CONTENT_TYPE_ERROR)

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
    def get_object(self, name: str) -> IO[bytes]:
        """Download an object as a stream.

        Args:
            name: Name/key of the object to download.

        Returns:
            IO[bytes] stream of the object data.

        Raises:
            ValueError: If name is invalid.
            ObjectNotFoundError: If the object does not exist.
            ObjectOperationError: If the download fails.
        """
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)

        try:
            return self._blob_client(name).download_blob()
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
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)

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
        if not isinstance(prefix, str):
            raise ValueError(INVALID_PREFIX_TYPE_ERROR)

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
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)

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
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)

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
