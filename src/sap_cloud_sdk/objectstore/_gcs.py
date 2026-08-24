"""Google Cloud Storage backend implementation for object store operations."""

import os
from typing import IO, BinaryIO, List, NoReturn

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.objectstore._models import GcsBindingData, ObjectMetadata
from sap_cloud_sdk.objectstore._validation import (
    EMPTY_CONTENT_TYPE_ERROR,
    EMPTY_FILE_PATH_ERROR,
    EMPTY_NAME_ERROR,
    INVALID_DATA_TYPE_ERROR,
    INVALID_PREFIX_TYPE_ERROR,
    INVALID_STREAM_ERROR,
    NEGATIVE_SIZE_ERROR,
)
from sap_cloud_sdk.objectstore.config import build_gcs_client
from sap_cloud_sdk.objectstore.exceptions import (
    ClientCreationError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)


class GcsClient:
    """Google Cloud Storage object storage client.

    Provides the standard 8-method object store interface backed by
    Google Cloud Storage. Obtain an instance via ``create_client()``.
    """

    def __init__(self, creds_config: GcsBindingData) -> None:
        """Initialise the GCS object storage client.

        Args:
            creds_config: GCS credentials.

        Raises:
            ClientCreationError: If client initialisation fails.
        """
        try:
            self._client = build_gcs_client(creds_config)
            self._bucket = self._client.bucket(creds_config.bucket)
        except ClientCreationError:
            raise
        except Exception as e:
            raise ClientCreationError(f"Failed to initialise GcsClient: {e}") from e

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
            blob = self._bucket.blob(name)
            blob.upload_from_string(data, content_type=content_type)
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
            blob = self._bucket.blob(name)
            blob.upload_from_file(stream, size=size, content_type=content_type)
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
            if not os.path.isfile(file_path):
                raise ObjectOperationError(f"File not found: {file_path}")

            blob = self._bucket.blob(name)
            blob.upload_from_filename(file_path, content_type=content_type)
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
            blob = self._bucket.blob(name)
            blob.reload()  # raises NotFound eagerly if absent; maps to ObjectNotFoundError
            return blob.open("rb")
        except Exception as e:
            self._map_gcs_error(e, name, "download")

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
            blob = self._bucket.blob(name)
            blob.delete()
        except Exception as e:
            try:
                from google.cloud.exceptions import NotFound  # lazy

                if isinstance(e, NotFound):
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
            for blob in self._client.list_blobs(self._bucket, prefix=prefix):
                result.append(
                    ObjectMetadata(
                        key=blob.name,
                        last_modified=blob.updated,
                        etag=(blob.etag or "").strip('"'),
                        size=blob.size or 0,
                        storage_class=blob.storage_class,
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
            blob = self._bucket.get_blob(name)
            if blob is None:
                raise ObjectNotFoundError(f"Object '{name}' not found")
            return ObjectMetadata(
                key=blob.name,
                last_modified=blob.updated,
                etag=(blob.etag or "").strip('"'),
                size=blob.size or 0,
                storage_class=blob.storage_class,
                owner=None,
            )
        except ObjectNotFoundError:
            raise
        except Exception as e:
            raise ObjectOperationError(
                f"Failed to get metadata for object '{name}': {e}"
            ) from e

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

    def _map_gcs_error(self, exc: Exception, name: str, operation: str) -> NoReturn:
        """Map GCS SDK exceptions to objectstore exceptions and re-raise."""
        try:
            from google.cloud.exceptions import NotFound  # lazy

            if isinstance(exc, NotFound):
                raise ObjectNotFoundError(f"Object '{name}' not found") from exc
        except ImportError:
            pass
        raise ObjectOperationError(
            f"Failed to {operation} object '{name}': {exc}"
        ) from exc
