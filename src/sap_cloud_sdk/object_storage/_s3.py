"""S3 backend implementation for object store operations using MinIO client."""

import io
import os
import threading
from datetime import UTC, datetime
from typing import Any, BinaryIO, Callable, List, TypeVar

import minio.datatypes
from minio import Minio
from minio.error import S3Error

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.object_storage.config import S3Config
from sap_cloud_sdk.object_storage._models import ObjectMetadata
from sap_cloud_sdk.object_storage._protocol import ObjectReader
from sap_cloud_sdk.object_storage._validation import (
    validate_object_name,
    validate_prefix,
    validate_put_from_bytes,
    validate_put_from_file,
    validate_put_object,
)
from sap_cloud_sdk.object_storage.exceptions import (
    ClientCreationError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)

_S3_NOT_FOUND_CODES = {"NoSuchKey", "NoSuchObject"}

# S3 error codes that indicate credential rejection (trigger reactive refresh).
_CREDENTIAL_ERROR_CODES = frozenset({"InvalidAccessKeyId", "SignatureDoesNotMatch"})

_T = TypeVar("_T")


def _normalize_host(host: str) -> str:
    """Normalize AWS S3 regional endpoints to standard format.

    Converts s3-{region}.amazonaws.com to s3.{region}.amazonaws.com
    to prevent Minio client from incorrectly transforming URLs.

    Args:
        host: The original host endpoint

    Returns:
        Normalized host endpoint
    """
    if host.startswith("s3-") and host.endswith(".amazonaws.com"):
        return host.replace("s3-", "s3.", 1)
    return host


class S3Client:
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
        config_factory: Callable[[], S3Config],
    ) -> None:
        """Initialize the object storage client.

        Args:
            config_factory: Factory that re-reads S3 configuration on every call.
                A :class:`~sap_cloud_sdk.core.secret_resolver.ConfigFactory` enables
                rotation tracking; a plain callable disables it.

        Raises:
            ClientCreationError: If client initialization fails.
        """
        self._config_factory = config_factory
        self._lock = threading.Lock()
        self._config = config_factory()
        self._minio_client = self._create_minio_client()

    def _create_minio_client(self) -> Minio:
        """Create MinIO client from the current credentials config."""
        try:
            return Minio(
                endpoint=_normalize_host(self._config.host),
                access_key=self._config.access_key_id,
                secret_key=self._config.secret_access_key,
                secure=not self._config.disable_ssl,
            )

        except Exception as e:
            raise ClientCreationError("Failed to create S3 object store client") from e

    def _refresh_credentials(self) -> None:
        """Re-read credentials and rebuild the MinIO client. Caller must hold ``_lock``."""
        self._config = self._config_factory()
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
        validate_put_from_bytes(name, data, content_type)

        try:
            self._execute_with_retry(
                lambda: self._minio_client.put_object(
                    bucket_name=self._config.bucket,
                    object_name=name,
                    data=io.BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                )
            )
        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object '{name}'") from e

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
        validate_put_object(name, stream, size, content_type)

        try:
            self._execute_with_retry(
                lambda: self._minio_client.put_object(
                    bucket_name=self._config.bucket,
                    object_name=name,
                    data=stream,
                    length=size,
                    content_type=content_type,
                )
            )
        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object '{name}'") from e

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
        validate_put_from_file(name, file_path, content_type)

        try:
            # Check if file exists and get size
            if not os.path.isfile(file_path):
                raise ObjectOperationError(f"File not found: {file_path}")

            file_size = os.path.getsize(file_path)

            with open(file_path, "rb") as file_stream:
                self._execute_with_retry(
                    lambda: self._minio_client.put_object(
                        bucket_name=self._config.bucket,
                        object_name=name,
                        data=file_stream,
                        length=file_size,
                        content_type=content_type,
                    )
                )
        except ObjectOperationError:
            raise
        except Exception as e:
            raise ObjectOperationError(f"Failed to upload object '{name}'") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_GET_OBJECT)
    def get_object(self, name: str) -> ObjectReader:
        """Download an object as a stream.

        Args:
            name: Name/key of the object to download

        Returns:
            A readable binary stream of the object data

        Raises:
            ValueError: If name is invalid
            ObjectNotFoundError: If the object doesn't exist
            ObjectOperationError: If the download fails
        """
        validate_object_name(name)

        try:
            response = self._execute_with_retry(
                lambda: self._minio_client.get_object(
                    bucket_name=self._config.bucket, object_name=name
                )
            )
            return response
        except S3Error as e:
            if e.code in _S3_NOT_FOUND_CODES:
                raise ObjectNotFoundError(f"Object '{name}' not found") from e
            raise ObjectOperationError(f"Failed to download object '{name}'") from e
        except Exception as e:
            raise ObjectOperationError(f"Failed to download object '{name}'") from e

    @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_DELETE_OBJECT)
    def delete_object(self, name: str) -> None:
        """Delete an object.

        Args:
            name: Name/key of the object to delete

        Raises:
            ValueError: If name is invalid
            ObjectOperationError: If the deletion fails
        """
        validate_object_name(name)

        try:
            self._execute_with_retry(
                lambda: self._minio_client.remove_object(
                    bucket_name=self._config.bucket, object_name=name
                )
            )
        except S3Error as e:
            if e.code not in _S3_NOT_FOUND_CODES:
                raise ObjectOperationError(f"Failed to delete object '{name}'") from e
            # For NoSuchKey, we still consider it successful (idempotent delete)
        except Exception as e:
            raise ObjectOperationError(f"Failed to delete object '{name}'") from e

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
        validate_prefix(prefix)

        result = []
        try:
            objects = self._execute_with_retry(
                lambda: self._minio_client.list_objects(
                    bucket_name=self._config.bucket, prefix=prefix
                )
            )

            for obj in objects:
                metadata = ObjectMetadata(
                    key=obj.object_name,
                    last_modified=obj.last_modified or datetime.min.replace(tzinfo=UTC),
                    etag=(obj.etag or "").strip('"'),
                    size=obj.size,
                    storage_class=obj.storage_class,
                    owner=obj.owner_name,
                )
                result.append(metadata)

            return result
        except Exception as e:
            raise ListObjectsError(
                f"Failed to list objects with prefix '{prefix}'"
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
        validate_object_name(name)

        try:
            stat: minio.datatypes.Object = self._execute_with_retry(
                lambda: self._minio_client.stat_object(
                    bucket_name=self._config.bucket, object_name=name
                )
            )

            return ObjectMetadata(
                key=name,
                last_modified=stat.last_modified or datetime.min.replace(tzinfo=UTC),
                etag=(stat.etag or "").strip('"'),  # Remove quotes from etag
                size=stat.size or 0,
                storage_class=None,  # stat_object doesn't provide storage class
                owner=None,  # stat_object doesn't provide owner
            )
        except S3Error as e:
            if e.code in _S3_NOT_FOUND_CODES:
                raise ObjectNotFoundError(f"Object '{name}' not found") from e
            raise ObjectOperationError(
                f"Failed to get metadata for object '{name}'"
            ) from e
        except Exception as e:
            raise ObjectOperationError(
                f"Failed to get metadata for object '{name}'"
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
        validate_object_name(name)

        try:
            self.head_object(name)
            return True
        except ObjectNotFoundError:
            return False
        except ObjectOperationError:
            raise
        except Exception as e:
            raise ObjectOperationError(
                f"Failed to check if object '{name}' exists"
            ) from e
