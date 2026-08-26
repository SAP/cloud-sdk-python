"""Google Cloud Storage backend implementation for object store operations."""

import os
from typing import IO, BinaryIO, List, NoReturn

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.objectstore.config import GcsConfig
from sap_cloud_sdk.objectstore._models import ObjectMetadata
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


class GcsClient:
    """Google Cloud Storage object storage client.

    Provides the standard 8-method object store interface backed by
    Google Cloud Storage. Obtain an instance via ``create_client()``.
    """

    def __init__(self, config: GcsConfig) -> None:
        """Initialise the GCS object storage client.

        Args:
            config: GCS client configuration.

        Raises:
            ClientCreationError: If client initialisation fails.
        """
        try:
            self._client = self._create_storage_client(config)
            self._bucket = self._client.bucket(config.bucket)
        except ClientCreationError:
            raise
        except Exception as e:
            raise ClientCreationError(f"Failed to initialise GcsClient: {e}") from e

    def _create_storage_client(self, cfg: GcsConfig):
        """Build a Google Cloud Storage Client from binding data.

        Decodes the base64-encoded service-account JSON and creates a
        storage.Client using the embedded credentials.
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
            raise ClientCreationError(
                f"Failed to create GCS storage client: {e}"
            ) from e

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
        validate_put_object(name, stream, size, content_type)

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
        validate_put_from_file(name, file_path, content_type)

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
        validate_object_name(name)

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
        validate_object_name(name)

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
        validate_prefix(prefix)

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
        validate_object_name(name)

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
