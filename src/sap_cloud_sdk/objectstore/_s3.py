"""S3 backend implementation for object store operations using MinIO client."""

import io
import os
import logging
from datetime import datetime
from http.client import HTTPResponse
from typing import BinaryIO, List, cast

import minio.datatypes
from minio import Minio
from minio.error import S3Error

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.objectstore.exceptions import (
    ClientCreationError,
    ObjectOperationError,
    ObjectNotFoundError,
    ListObjectsError,
)
from sap_cloud_sdk.objectstore._models import ObjectStoreBindingData, ObjectMetadata
from sap_cloud_sdk.core.auditlog import (
    create_client as create_auditlog_client,
    DataAccessEvent,
    DataModificationEvent,
    DataDeletionEvent,
    DataAccessAttribute,
    ChangeAttribute,
    DeletedAttribute,
    Tenant,
)
from sap_cloud_sdk.objectstore.utils import _normalize_host

# Validation error message constants
EMPTY_NAME_ERROR = "name must be a non-empty string"
EMPTY_CONTENT_TYPE_ERROR = "content_type must be a non-empty string"
EMPTY_FILE_PATH_ERROR = "file_path must be a non-empty string"
INVALID_DATA_TYPE_ERROR = "data must be bytes"
INVALID_STREAM_ERROR = "stream must be a readable binary stream"
NEGATIVE_SIZE_ERROR = "size must be non-negative"
INVALID_PREFIX_TYPE_ERROR = "prefix must be a string"


class ObjectStoreClient:
    """S3-compatible object storage client.

    Provides a unified interface for object storage operations using the MinIO client library.
    Supports upload, download, delete, list, and metadata operations on S3-compatible storage.
    """

    def __init__(
        self, creds_config: ObjectStoreBindingData, *, disable_ssl: bool = False
    ) -> None:
        """Initialize the object storage client.

        Args:
            creds_config: Connection credentials and endpoint configuration.
            disable_ssl: Whether to disable SSL/TLS connections. Defaults to False.

        Raises:
            ClientCreationError: If client initialization fails.
        """

        self._creds_config = creds_config
        self._disable_ssl = disable_ssl
        self._minio_client = self._create_minio_client()
        # Pass Module.OBJECTSTORE as source when creating auditlog client
        self._audit_client = create_auditlog_client(
            _telemetry_source=Module.OBJECTSTORE
        )

    def _create_minio_client(self) -> Minio:
        """Create MinIO client with proper configuration."""
        try:
            return Minio(
                endpoint=_normalize_host(self._creds_config.host),
                access_key=self._creds_config.access_key_id,
                secret_key=self._creds_config.secret_access_key,
                secure=not self._disable_ssl,
            )

        except Exception as e:
            raise ClientCreationError(f"Failed to create MinIO client: {e}") from e

    def _build_data_access_event(
        self, object_name: str, success: bool
    ) -> DataAccessEvent:
        """Build a data access audit event for read operations."""
        return DataAccessEvent(
            object_type="s3-object",
            object_id={"bucket": self._creds_config.bucket, "key": object_name},
            subject_type="application",
            subject_id={"type": "automation"},
            subject_role="app-foundation-sdk-python",
            attributes=[DataAccessAttribute(name=object_name, successful=success)],
            user="app-foundation-sdk-python",
            tenant=Tenant.PROVIDER,
        )

    def _build_data_modification_event(self, object_name: str) -> DataModificationEvent:
        return DataModificationEvent(
            object_type="s3-object",
            object_id={"bucket": self._creds_config.bucket, "key": object_name},
            subject_type="application",
            subject_id={"type": "automation"},
            subject_role="app-foundation-sdk-python",
            attributes=[ChangeAttribute(name=object_name, new="", old="")],
            user="app-foundation-sdk-python",
            tenant=Tenant.PROVIDER,
        )

    def _build_data_deletion_event(self, object_name: str) -> DataDeletionEvent:
        """Build a data deletion audit event for delete operations."""
        return DataDeletionEvent(
            object_type="s3-object",
            object_id={"bucket": self._creds_config.bucket, "key": object_name},
            subject_type="application",
            subject_id={"type": "automation"},
            subject_role="app-foundation-sdk-python",
            attributes=[DeletedAttribute(name=object_name, old="")],
            user="app-foundation-sdk-python",
            tenant=Tenant.PROVIDER,
        )

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
            self._minio_client.put_object(
                bucket_name=self._creds_config.bucket,
                object_name=name,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )

            try:
                self._audit_client.log(self._build_data_modification_event(name))
            except Exception as e:
                logging.error(f"audit log failed for PutObjectFromBytes operation: {e}")

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
            self._minio_client.put_object(
                bucket_name=self._creds_config.bucket,
                object_name=name,
                data=stream,
                length=size,
                content_type=content_type,
            )

            try:
                self._audit_client.log(self._build_data_modification_event(name))
            except Exception as e:
                logging.error(f"audit log failed for PutObject operation: {e}")

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
            # Check if file exists and get size
            if not os.path.isfile(file_path):
                raise ObjectOperationError(f"File not found: {file_path}")

            file_size = os.path.getsize(file_path)

            # Single file operation - no content reading for audit
            with open(file_path, "rb") as file_stream:
                self._minio_client.put_object(
                    bucket_name=self._creds_config.bucket,
                    object_name=name,
                    data=file_stream,
                    length=file_size,
                    content_type=content_type,
                )

            try:
                self._audit_client.log(self._build_data_modification_event(name))
            except Exception as e:
                logging.error(f"audit log failed for PutObjectFromFile operation: {e}")

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

        get_err = None
        try:
            response = cast(HTTPResponse, self._minio_client.get_object(
                bucket_name=self._creds_config.bucket, object_name=name
            ))
            return response
        except S3Error as e:
            get_err = e
            if e.code == "NoSuchKey":
                raise ObjectNotFoundError(f"Object '{name}' not found") from e
            raise ObjectOperationError(
                f"Failed to download object '{name}': {e.code} - {e.message}"
            ) from e
        except Exception as e:
            get_err = e
            raise ObjectOperationError(
                f"Failed to download object '{name}': {e}"
            ) from e
        finally:
            # Log audit event
            try:
                self._audit_client.log(
                    self._build_data_access_event(name, get_err is None)
                )
            except Exception as e:
                logging.error(f"audit log failed for GetObject operation: {e}")

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
            self._minio_client.remove_object(
                bucket_name=self._creds_config.bucket, object_name=name
            )

            try:
                self._audit_client.log(self._build_data_deletion_event(name))
            except Exception as e:
                logging.error(f"audit log failed for DeleteObject operation: {e}")

        except S3Error as e:
            if e.code != "NoSuchKey":
                raise ObjectOperationError(
                    f"Failed to delete object '{name}': {e.code} - {e.message}"
                ) from e
            # For NoSuchKey, we still consider it successful (idempotent delete)
            try:
                self._audit_client.log(self._build_data_deletion_event(name))
            except Exception as audit_e:
                logging.error(f"audit log failed for DeleteObject operation: {audit_e}")
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

        list_err = None
        result = []
        try:
            objects = self._minio_client.list_objects(
                bucket_name=self._creds_config.bucket, prefix=prefix
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
            list_err = e
            raise ListObjectsError(
                f"Failed to list objects with prefix '{prefix}': {e.code} - {e.message}"
            ) from e
        except Exception as e:
            list_err = e
            raise ListObjectsError(
                f"Failed to list objects with prefix '{prefix}': {e}"
            ) from e
        finally:
            if prefix is None or prefix.strip() == "":
                # Audit log name can't be empty
                prefix = "/"
            try:
                self._audit_client.log(
                    self._build_data_access_event(prefix, list_err is None)
                )
            except Exception as e:
                logging.error(f"audit log failed for ListObjects operation: {e}")

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

        head_err = None
        try:
            stat: minio.datatypes.Object = self._minio_client.stat_object(
                bucket_name=self._creds_config.bucket, object_name=name
            )

            return ObjectMetadata(
                key=name,
                last_modified=stat.last_modified or datetime.min,
                etag=(stat.etag or "").strip('"'),  # Remove quotes from etag
                size=stat.size or 0,
                storage_class=None,  # stat_object doesn't provide storage class
                owner=None,  # stat_object doesn't provide owner
            )
        except S3Error as e:
            head_err = e
            if e.code == "NoSuchKey":
                raise ObjectNotFoundError(f"Object '{name}' not found") from e
            raise ObjectOperationError(
                f"Failed to get metadata for object '{name}': {e.code} - {e.message}"
            ) from e
        except Exception as e:
            head_err = e
            raise ObjectOperationError(
                f"Failed to get metadata for object '{name}': {e}"
            ) from e
        finally:
            try:
                self._audit_client.log(
                    self._build_data_access_event(name, head_err is None)
                )
            except Exception as e:
                logging.error(f"audit log failed for HeadObject operation: {e}")

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
