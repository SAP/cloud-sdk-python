"""S3 backend implementation for object store operations using MinIO client."""

import io
import logging
import os
import threading
from datetime import datetime
from http.client import HTTPResponse
from typing import TYPE_CHECKING, Any, BinaryIO, Callable, List, TypeVar, cast

import minio.datatypes
from minio import Minio
from minio.error import S3Error

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.objectstore.exceptions import (
    ClientCreationError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)
from sap_cloud_sdk.objectstore._models import ObjectStoreBindingData, ObjectMetadata
from sap_cloud_sdk.objectstore.utils import _normalize_host

if TYPE_CHECKING:
    from sap_cloud_sdk.core.secret_resolver import ConfigFactory

logger = logging.getLogger(__name__)

# Validation error message constants
EMPTY_NAME_ERROR = "name must be a non-empty string"
EMPTY_CONTENT_TYPE_ERROR = "content_type must be a non-empty string"
EMPTY_FILE_PATH_ERROR = "file_path must be a non-empty string"
INVALID_DATA_TYPE_ERROR = "data must be bytes"
INVALID_STREAM_ERROR = "stream must be a readable binary stream"
NEGATIVE_SIZE_ERROR = "size must be non-negative"
INVALID_PREFIX_TYPE_ERROR = "prefix must be a string"

# S3 error codes that indicate credential rejection (trigger reactive refresh)
_CREDENTIAL_ERROR_CODES = frozenset({"InvalidAccessKeyId", "SignatureDoesNotMatch"})

_T = TypeVar("_T")


class ObjectStoreClient:
    """S3-compatible object storage client with binding-rotation support.

    Provides a unified interface for object storage operations using the MinIO client library.
    Supports upload, download, delete, list, and metadata operations on S3-compatible storage.

    Rotation resilience is handled in two layers:
    - **Proactive**: checks the secret-directory mtime via the config factory's
      ``has_changed()`` method before every operation and rebuilds the MinIO client
      when a change is detected.
    - **Reactive**: on ``InvalidAccessKeyId`` or ``SignatureDoesNotMatch`` S3 errors,
      refreshes credentials and retries the operation exactly once.
    """

    def __init__(
        self,
        config_factory: "ConfigFactory[ObjectStoreBindingData]",
        *,
        disable_ssl: bool = False,
    ) -> None:
        """Initialize the object storage client.

        Args:
            config_factory: Factory that re-reads S3 credentials on every call.
                Must implement the :class:`~sap_cloud_sdk.core.secret_resolver.ConfigFactory`
                protocol (callable + optional ``has_changed()``).
            disable_ssl: Whether to disable SSL/TLS connections. Defaults to False.

        Raises:
            ClientCreationError: If client initialization fails.
        """
        self._config_factory = config_factory
        self._disable_ssl = disable_ssl
        self._lock = threading.Lock()
        self._creds_config = config_factory()
        self._minio_client = self._create_minio_client()

    def _create_minio_client(self) -> Minio:
        """Create MinIO client from the current credentials config."""
        try:
            return Minio(
                endpoint=_normalize_host(self._creds_config.host),
                access_key=self._creds_config.access_key_id,
                secret_key=self._creds_config.secret_access_key,
                secure=not self._disable_ssl,
            )
        except Exception as e:
            raise ClientCreationError(f"Failed to create MinIO client: {e}") from e

    def _refresh_credentials(self) -> None:
        """Re-read credentials and rebuild the MinIO client. Caller must hold ``_lock``."""
        self._creds_config = self._config_factory()
        self._minio_client = self._create_minio_client()

    def _refresh_if_rotated(self) -> None:
        """Proactively refresh if the secret directory mtime has changed."""
        has_changed: Any = getattr(self._config_factory, "has_changed", None)
        if callable(has_changed) and has_changed():
            with self._lock:
                self._refresh_credentials()

    def _execute_with_retry(self, fn: Callable[[], _T]) -> _T:
        """Run *fn* against the current MinIO client, retrying once on credential errors.

        Calls ``_refresh_if_rotated()`` first (proactive), then executes *fn*.
        On ``InvalidAccessKeyId`` or ``SignatureDoesNotMatch``, refreshes credentials
        and retries exactly once (reactive).
        """
        self._refresh_if_rotated()
        try:
            return fn()
        except S3Error as e:
            if e.code in _CREDENTIAL_ERROR_CODES:
                with self._lock:
                    self._refresh_credentials()
                return fn()
            raise

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_PUT_OBJECT_FROM_BYTES)
    def put_object_from_bytes(self, name: str, data: bytes, content_type: str) -> None:
        """Upload an object from bytes.

        Args:
            name: Name/key of the object to upload
            data: Byte data to upload
            content_type: MIME type of the object

        Raises:
            ValueError: If any parameter is invalid
            ObjectOperationError: If the upload fails
        """
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)
        if not isinstance(data, bytes):
            raise ValueError(INVALID_DATA_TYPE_ERROR)
        if not content_type:
            raise ValueError(EMPTY_CONTENT_TYPE_ERROR)

        try:
            self._execute_with_retry(
                lambda: self._minio_client.put_object(
                    bucket_name=self._creds_config.bucket,
                    object_name=name,
                    data=io.BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                )
            )
        except S3Error as e:
            raise ObjectOperationError(
                f"Failed to upload object '{name}': {e.code} - {e.message}"
            ) from e
        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object '{name}': {e}") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_PUT_OBJECT)
    def put_object(
        self, name: str, stream: BinaryIO, size: int, content_type: str
    ) -> None:
        """Upload an object from a stream.

        Args:
            name: Name/key of the object to upload
            stream: Binary stream containing the object data
            size: Size of the object in bytes
            content_type: MIME type of the object

        Raises:
            ValueError: If any parameter is invalid
            ObjectOperationError: If the upload fails
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
            self._execute_with_retry(
                lambda: self._minio_client.put_object(
                    bucket_name=self._creds_config.bucket,
                    object_name=name,
                    data=stream,
                    length=size,
                    content_type=content_type,
                )
            )
        except S3Error as e:
            raise ObjectOperationError(
                f"Failed to upload object '{name}': {e.code} - {e.message}"
            ) from e
        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object '{name}': {e}") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_PUT_OBJECT_FROM_FILE)
    def put_object_from_file(
        self, name: str, file_path: str, content_type: str
    ) -> None:
        """Upload an object from a local file.

        Args:
            name: Name/key of the object to upload
            file_path: Path to the local file to upload
            content_type: MIME type of the object

        Raises:
            ValueError: If any parameter is invalid
            ObjectOperationError: If the upload fails
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

            file_size = os.path.getsize(file_path)

            with open(file_path, "rb") as file_stream:
                self._execute_with_retry(
                    lambda: self._minio_client.put_object(
                        bucket_name=self._creds_config.bucket,
                        object_name=name,
                        data=file_stream,
                        length=file_size,
                        content_type=content_type,
                    )
                )
        except S3Error as e:
            raise ObjectOperationError(
                f"Failed to upload object '{name}': {e.code} - {e.message}"
            ) from e
        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object '{name}': {e}") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_GET_OBJECT)
    def get_object(self, name: str) -> HTTPResponse:
        """Download an object as a stream.

        Args:
            name: Name/key of the object to download

        Returns:
            HTTPResponse stream of the object data

        Raises:
            ValueError: If name is invalid
            ObjectNotFoundError: If the object doesn't exist
            ObjectOperationError: If the download fails
        """
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)

        try:
            response = cast(
                HTTPResponse,
                self._execute_with_retry(
                    lambda: self._minio_client.get_object(
                        bucket_name=self._creds_config.bucket, object_name=name
                    )
                ),
            )
            return response
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise ObjectNotFoundError(f"Object '{name}' not found") from e
            raise ObjectOperationError(
                f"Failed to download object '{name}': {e.code} - {e.message}"
            ) from e
        except Exception as e:
            raise ObjectOperationError(
                f"Failed to download object '{name}': {e}"
            ) from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_DELETE_OBJECT)
    def delete_object(self, name: str) -> None:
        """Delete an object.

        Args:
            name: Name/key of the object to delete

        Raises:
            ValueError: If name is invalid
            ObjectOperationError: If the deletion fails
        """
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)

        try:
            self._execute_with_retry(
                lambda: self._minio_client.remove_object(
                    bucket_name=self._creds_config.bucket, object_name=name
                )
            )
        except S3Error as e:
            if e.code != "NoSuchKey":
                raise ObjectOperationError(
                    f"Failed to delete object '{name}': {e.code} - {e.message}"
                ) from e
            # NoSuchKey is treated as a successful idempotent delete
        except Exception as e:
            raise ObjectOperationError(f"Failed to delete object '{name}': {e}") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_LIST_OBJECTS)
    def list_objects(self, prefix: str) -> List[ObjectMetadata]:
        """List objects with a given prefix.

        Args:
            prefix: Prefix to filter objects by name

        Returns:
            List of object metadata

        Raises:
            ValueError: If prefix is invalid
            ListObjectsError: If listing fails
        """
        if not isinstance(prefix, str):
            raise ValueError(INVALID_PREFIX_TYPE_ERROR)

        result = []
        try:
            objects = self._execute_with_retry(
                lambda: self._minio_client.list_objects(
                    bucket_name=self._creds_config.bucket, prefix=prefix
                )
            )

            for obj in objects:
                metadata = ObjectMetadata(
                    key=obj.object_name,
                    last_modified=obj.last_modified,
                    etag=obj.etag,
                    size=obj.size,
                    storage_class=obj.storage_class,
                    owner=obj.owner_name,
                )
                result.append(metadata)

            return result
        except S3Error as e:
            raise ListObjectsError(
                f"Failed to list objects with prefix '{prefix}': {e.code} - {e.message}"
            ) from e
        except Exception as e:
            raise ListObjectsError(
                f"Failed to list objects with prefix '{prefix}': {e}"
            ) from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_HEAD_OBJECT)
    def head_object(self, name: str) -> ObjectMetadata:
        """Get metadata for an object without downloading it.

        Args:
            name: Name/key of the object

        Returns:
            Object metadata

        Raises:
            ValueError: If name is invalid
            ObjectNotFoundError: If the object doesn't exist
            ObjectOperationError: If the operation fails
        """
        if not name:
            raise ValueError(EMPTY_NAME_ERROR)

        try:
            stat: minio.datatypes.Object = self._execute_with_retry(
                lambda: self._minio_client.stat_object(
                    bucket_name=self._creds_config.bucket, object_name=name
                )
            )

            return ObjectMetadata(
                key=name,
                last_modified=stat.last_modified or datetime.min,
                etag=(stat.etag or "").strip('"'),
                size=stat.size or 0,
                storage_class=None,
                owner=None,
            )
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise ObjectNotFoundError(f"Object '{name}' not found") from e
            raise ObjectOperationError(
                f"Failed to get metadata for object '{name}': {e.code} - {e.message}"
            ) from e
        except Exception as e:
            raise ObjectOperationError(
                f"Failed to get metadata for object '{name}': {e}"
            ) from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_OBJECT_EXISTS)
    def object_exists(self, name: str) -> bool:
        """Check if an object exists.

        Args:
            name: Name/key of the object to check

        Returns:
            True if the object exists, False otherwise

        Raises:
            ValueError: If name is invalid
            ObjectOperationError: If the check fails
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
