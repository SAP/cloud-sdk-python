"""Google Cloud Storage backend implementation for object store operations."""

import base64
import json
import os
import threading
from typing import Any, BinaryIO, Callable, List, NoReturn, TypeVar

from google.api_core.exceptions import Forbidden, Unauthenticated
from google.auth.exceptions import RefreshError
from google.cloud import storage
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account

from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
from sap_cloud_sdk.object_storage.config import GcsConfig
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

# GCS errors that indicate credential rejection (trigger reactive refresh).
# RefreshError: failure minting an OAuth token from the service-account key.
# Forbidden / Unauthenticated: 403 / 401 rejection on the request itself.
_CREDENTIAL_ERRORS = (RefreshError, Forbidden, Unauthenticated)

_T = TypeVar("_T")


class GcsClient:
    """Google Cloud Storage object storage client with binding-rotation support.

    Provides the standard 8-method object store interface backed by
    Google Cloud Storage. Obtain an instance via ``create_client()``.

    Rotation resilience is handled in two layers:
    - **Proactive**: checks the secret-directory mtime via the config factory's
      ``has_changed()`` method before every operation and rebuilds the storage
      client when a change is detected.
    - **Reactive**: on a credential-rejection error (``RefreshError`` when minting a
      token, or ``Forbidden`` / ``Unauthenticated`` on the request), refreshes
      credentials and retries the operation exactly once.
    """

    def __init__(
        self,
        config_factory: Callable[[], GcsConfig],
    ) -> None:
        """Initialise the GCS object storage client.

        Args:
            config_factory: Factory that re-reads GCS configuration on every call.
                A :class:`~sap_cloud_sdk.core.secret_resolver.ConfigFactory` enables
                rotation tracking; a plain callable disables it.

        Raises:
            ClientCreationError: If client initialisation fails.
        """
        self._config_factory = config_factory
        self._lock = threading.Lock()
        self._config = config_factory()
        self._client = self._create_storage_client(self._config)
        self._bucket = self._client.bucket(self._config.bucket)

    def _create_storage_client(self, cfg: GcsConfig) -> storage.Client:
        """Build a Google Cloud Storage Client from binding data.

        Decodes the base64-encoded service-account JSON and creates a
        storage.Client using the embedded credentials.
        """
        try:
            info = json.loads(base64.b64decode(cfg.base64_encoded_private_key_data))
            creds = service_account.Credentials.from_service_account_info(info)
            return storage.Client(project=cfg.project_id, credentials=creds)
        except Exception as e:
            raise ClientCreationError(
                "Failed to create Google Cloud Storage client"
            ) from e

    def _refresh_credentials(self) -> None:
        """Re-read credentials and rebuild the storage client. Caller must hold ``_lock``."""
        self._config = self._config_factory()
        self._client = self._create_storage_client(self._config)
        self._bucket = self._client.bucket(self._config.bucket)

    def _refresh_if_rotated(self) -> None:
        """Proactively refresh if the secret directory mtime has changed."""
        has_changed: Any = getattr(self._config_factory, "has_changed", None)
        if callable(has_changed) and has_changed():
            with self._lock:
                self._refresh_credentials()

    def _execute_with_retry(self, fn: Callable[[], _T]) -> _T:
        """Run *fn* against the current storage client, retrying once on credential errors.

        Calls ``_refresh_if_rotated()`` first (proactive), then executes *fn*. On a
        ``RefreshError``, ``Forbidden`` or ``Unauthenticated``, refreshes credentials
        and retries exactly once (reactive).
        """
        self._refresh_if_rotated()
        try:
            return fn()
        except _CREDENTIAL_ERRORS:
            with self._lock:
                self._refresh_credentials()
            return fn()

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
            self._execute_with_retry(
                lambda: self._bucket.blob(name).upload_from_string(
                    data,
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
            self._execute_with_retry(
                lambda: self._bucket.blob(name).upload_from_file(
                    stream,
                    size=size,
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

            self._execute_with_retry(
                lambda: self._bucket.blob(name).upload_from_filename(
                    file_path,
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
            blob = self._execute_with_retry(lambda: self._reloaded_blob(name))
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
            self._execute_with_retry(lambda: self._bucket.blob(name).delete())
        except Exception as e:
            if self._is_not_found(e):
                self._confirm_bucket_exists(e, name, "delete")
                return  # idempotent
            raise ObjectOperationError(f"Failed to delete object '{name}'") from e

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
            blobs = self._execute_with_retry(
                lambda: list(self._client.list_blobs(self._bucket, prefix=prefix))
            )
            for blob in blobs:
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
                f"Failed to list objects with prefix '{prefix}'"
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
            blob = self._execute_with_retry(lambda: self._reloaded_blob(name))
            return ObjectMetadata(
                key=blob.name,
                last_modified=blob.updated,
                etag=(blob.etag or "").strip('"'),
                size=blob.size or 0,
                storage_class=blob.storage_class,
                owner=None,
            )
        except Exception as e:
            self._map_gcs_error(e, name, "get metadata for")

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
        except ObjectOperationError:
            raise
        except Exception as e:
            raise ObjectOperationError(
                f"Failed to check if object '{name}' exists"
            ) from e

    def _reloaded_blob(self, name: str):
        """Return a freshly reloaded blob bound to the current bucket.

        Reloading raises ``NotFound`` eagerly for absent objects and surfaces
        credential errors so the retry wrapper can act on them.
        """
        blob = self._bucket.blob(name)
        blob.reload()
        return blob

    @staticmethod
    def _is_not_found(exc: Exception) -> bool:
        """Return whether Google Cloud Storage returned HTTP 404."""
        return isinstance(exc, NotFound)

    def _confirm_bucket_exists(self, exc: Exception, name: str, operation: str) -> None:
        """Ensure a 404 belongs to an object in an available bucket."""
        try:
            bucket_exists = self._bucket.exists()
        except Exception as verification_error:
            raise ObjectOperationError(
                f"Failed to {operation} object '{name}'"
            ) from verification_error
        if not bucket_exists:
            raise ObjectOperationError(
                f"Failed to {operation} object '{name}'"
            ) from exc

    def _map_gcs_error(self, exc: Exception, name: str, operation: str) -> NoReturn:
        """Map GCS SDK exceptions to objectstore exceptions and re-raise."""
        if self._is_not_found(exc):
            self._confirm_bucket_exists(exc, name, operation)
            raise ObjectNotFoundError(f"Object '{name}' not found") from exc
        raise ObjectOperationError(f"Failed to {operation} object '{name}'") from exc
