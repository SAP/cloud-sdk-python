"""Tests for S3 client functionality."""

import io
import os
from datetime import datetime
from http.client import HTTPResponse
from unittest.mock import Mock, call, patch, mock_open
import pytest
from minio.error import S3Error

from sap_cloud_sdk.objectstore._s3 import ObjectStoreClient
from sap_cloud_sdk.objectstore._models import ObjectStoreBindingData, ObjectMetadata
from sap_cloud_sdk.objectstore.exceptions import (
    ClientCreationError, ObjectOperationError, ObjectNotFoundError, ListObjectsError
)


def _make_creds(
    *,
    access_key_id: str = "test_key",
    secret_access_key: str = "test_secret",
    bucket: str = "test-bucket",
    host: str = "s3.amazonaws.com",
) -> ObjectStoreBindingData:
    return ObjectStoreBindingData(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        bucket=bucket,
        host=host,
    )


def _make_factory(
    creds: ObjectStoreBindingData | None = None,
    *,
    has_changed: bool = False,
) -> Mock:
    """Return a mock config factory with controllable ``has_changed()``."""
    if creds is None:
        creds = _make_creds()
    factory = Mock(return_value=creds)
    factory.has_changed = Mock(return_value=has_changed)
    return factory


def _make_s3_error(code: str) -> S3Error:
    return S3Error(code, "error message", "resource", "request-id", "host-id", Mock())


class TestObjectStoreClient:

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_client_creation_ssl_enabled(self, mock_minio_class):
        mock_minio_class.return_value = Mock()
        client = ObjectStoreClient(_make_factory(), disable_ssl=False)
        mock_minio_class.assert_called_once_with(
            endpoint="s3.amazonaws.com",
            access_key="test_key",
            secret_key="test_secret",
            secure=True,
        )
        assert client._minio_client == mock_minio_class.return_value

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_client_creation_ssl_disabled(self, mock_minio_class):
        mock_minio_class.return_value = Mock()
        ObjectStoreClient(_make_factory(), disable_ssl=True)
        mock_minio_class.assert_called_once_with(
            endpoint="s3.amazonaws.com",
            access_key="test_key",
            secret_key="test_secret",
            secure=False,
        )

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_client_creation_failure(self, mock_minio_class):
        mock_minio_class.side_effect = Exception("Connection failed")
        with pytest.raises(ClientCreationError, match="Failed to create MinIO client"):
            ObjectStoreClient(_make_factory())

    # ------------------------------------------------------------------
    # Proactive rotation — has_changed() returns True
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_proactive_rotation_rebuilds_minio_client(self, mock_minio_class):
        original_minio = Mock()
        rotated_minio = Mock()
        mock_minio_class.side_effect = [original_minio, rotated_minio]

        rotated_creds = _make_creds(access_key_id="new_key", secret_access_key="new_secret")
        # factory() is called once in __init__ (initial creds) and once in _refresh_credentials
        factory = Mock(side_effect=[_make_creds(), rotated_creds])
        # has_changed() is NOT called during __init__; it's first called by _refresh_if_rotated
        # inside put_object_from_bytes. Returning True on the first call triggers the refresh.
        factory.has_changed = Mock(return_value=True)

        client = ObjectStoreClient(factory)
        assert client._minio_client is original_minio

        client.put_object_from_bytes("f.txt", b"data", "text/plain")

        assert client._minio_client is rotated_minio
        assert client._creds_config is rotated_creds
        rotated_minio.put_object.assert_called_once()

    # ------------------------------------------------------------------
    # Reactive rotation — credential S3 errors trigger one retry
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("error_code", ["InvalidAccessKeyId", "SignatureDoesNotMatch"])
    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_reactive_rotation_retries_on_credential_error(self, mock_minio_class, error_code):
        original_minio = Mock()
        rotated_minio = Mock()
        mock_minio_class.side_effect = [original_minio, rotated_minio]

        rotated_creds = _make_creds(access_key_id="new_key")
        factory = Mock(side_effect=[_make_creds(), rotated_creds])
        factory.has_changed = Mock(return_value=False)

        original_minio.put_object.side_effect = _make_s3_error(error_code)
        rotated_minio.put_object.return_value = None

        client = ObjectStoreClient(factory)
        client.put_object_from_bytes("f.txt", b"data", "text/plain")

        assert original_minio.put_object.call_count == 1
        assert rotated_minio.put_object.call_count == 1
        assert client._creds_config is rotated_creds

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_non_credential_s3_error_is_not_retried(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio
        mock_minio.put_object.side_effect = _make_s3_error("AccessDenied")

        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ObjectOperationError, match="Failed to upload object"):
            client.put_object_from_bytes("f.txt", b"data", "text/plain")

        assert mock_minio.put_object.call_count == 1

    # ------------------------------------------------------------------
    # put_object_from_bytes
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_put_object_from_bytes_success(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        test_data = b"Hello, World!"

        client.put_object_from_bytes("test.txt", test_data, "text/plain")

        mock_minio.put_object.assert_called_once()
        call_args = mock_minio.put_object.call_args
        assert call_args.kwargs["bucket_name"] == "test-bucket"
        assert call_args.kwargs["object_name"] == "test.txt"
        assert call_args.kwargs["length"] == len(test_data)
        assert call_args.kwargs["content_type"] == "text/plain"
        assert isinstance(call_args.kwargs["data"], io.BytesIO)

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_put_object_from_bytes_validation(self, mock_minio_class):
        mock_minio_class.return_value = Mock()
        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.put_object_from_bytes("", b"data", "text/plain")

        with pytest.raises(ValueError, match="data must be bytes"):
            client.put_object_from_bytes("test.txt", "not bytes", "text/plain")  # ty: ignore[invalid-argument-type]

        with pytest.raises(ValueError, match="content_type must be a non-empty string"):
            client.put_object_from_bytes("test.txt", b"data", "")

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_put_object_from_bytes_s3_error(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio.put_object.side_effect = _make_s3_error("AccessDenied")
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ObjectOperationError, match="Failed to upload object"):
            client.put_object_from_bytes("test.txt", b"data", "text/plain")

    # ------------------------------------------------------------------
    # put_object (stream)
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_put_object_from_stream_success(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        stream = io.BytesIO(b"stream data")

        client.put_object("test.txt", stream, 11, "text/plain")

        mock_minio.put_object.assert_called_once()
        call_args = mock_minio.put_object.call_args
        assert call_args.kwargs["bucket_name"] == "test-bucket"
        assert call_args.kwargs["object_name"] == "test.txt"
        assert call_args.kwargs["length"] == 11
        assert call_args.kwargs["content_type"] == "text/plain"

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_put_object_validation(self, mock_minio_class):
        mock_minio_class.return_value = Mock()
        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ValueError, match="size must be non-negative"):
            client.put_object("test.txt", io.BytesIO(b"data"), -1, "text/plain")

    # ------------------------------------------------------------------
    # put_object_from_file
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    @patch("builtins.open", new_callable=mock_open, read_data=b"file content")
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.getsize", return_value=12)
    def test_put_object_from_file_success(self, mock_getsize, mock_isfile, mock_file, mock_minio_class):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        client.put_object_from_file("test.txt", "/path/to/file.txt", "text/plain")

        mock_isfile.assert_called_once_with("/path/to/file.txt")
        mock_getsize.assert_called_once_with("/path/to/file.txt")
        mock_minio.put_object.assert_called_once()

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    @patch("builtins.open", new_callable=mock_open, read_data=b"file content")
    @patch("os.path.isfile", return_value=False)
    def test_put_object_from_file_not_found(self, mock_isfile, mock_file, mock_minio_class):
        mock_minio_class.return_value = Mock()
        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ObjectOperationError, match="File not found"):
            client.put_object_from_file("test.txt", "/nonexistent.txt", "text/plain")

    # ------------------------------------------------------------------
    # get_object
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_get_object_success(self, mock_minio_class):
        mock_minio = Mock()
        mock_response = Mock(spec=HTTPResponse)
        mock_minio.get_object.return_value = mock_response
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        result = client.get_object("test.txt")

        mock_minio.get_object.assert_called_once_with(
            bucket_name="test-bucket", object_name="test.txt"
        )
        assert result == mock_response

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_get_object_not_found(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio.get_object.side_effect = _make_s3_error("NoSuchKey")
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ObjectNotFoundError, match="Object 'test.txt' not found"):
            client.get_object("test.txt")

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_get_object_empty_name_validation(self, mock_minio_class):
        mock_minio_class.return_value = Mock()
        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.get_object("")

    # ------------------------------------------------------------------
    # delete_object
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_delete_object_success(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        client.delete_object("test.txt")

        mock_minio.remove_object.assert_called_once_with(
            bucket_name="test-bucket", object_name="test.txt"
        )

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_delete_object_not_found_ignored(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio.remove_object.side_effect = _make_s3_error("NoSuchKey")
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        client.delete_object("test.txt")  # should not raise

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_delete_object_empty_name_validation(self, mock_minio_class):
        mock_minio_class.return_value = Mock()
        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.delete_object("")

    # ------------------------------------------------------------------
    # list_objects
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_list_objects_success(self, mock_minio_class):
        mock_minio = Mock()

        mock_obj1 = Mock()
        mock_obj1.object_name = "prefix/file1.txt"
        mock_obj1.last_modified = datetime(2023, 1, 1, 12, 0, 0)
        mock_obj1.etag = '"abc123"'
        mock_obj1.size = 100
        mock_obj1.storage_class = "STANDARD"
        mock_obj1.owner_name = "owner1"

        mock_minio.list_objects.return_value = [mock_obj1]
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        result = client.list_objects("prefix/")

        mock_minio.list_objects.assert_called_once_with(
            bucket_name="test-bucket", prefix="prefix/"
        )
        assert len(result) == 1
        assert result[0].key == "prefix/file1.txt"
        assert result[0].etag == '"abc123"'

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_list_objects_s3_error(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio.list_objects.side_effect = _make_s3_error("AccessDenied")
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ListObjectsError, match="Failed to list objects"):
            client.list_objects("prefix/")

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_list_objects_prefix_validation(self, mock_minio_class):
        mock_minio_class.return_value = Mock()
        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ValueError, match="prefix must be a string"):
            client.list_objects(123)  # ty: ignore[invalid-argument-type]

    # ------------------------------------------------------------------
    # head_object
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_head_object_success(self, mock_minio_class):
        mock_minio = Mock()

        mock_stat = Mock()
        mock_stat.last_modified = datetime(2023, 1, 1, 12, 0, 0)
        mock_stat.etag = '"abc123"'
        mock_stat.size = 100

        mock_minio.stat_object.return_value = mock_stat
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        result = client.head_object("test.txt")

        mock_minio.stat_object.assert_called_once_with(
            bucket_name="test-bucket", object_name="test.txt"
        )
        assert result.key == "test.txt"
        assert result.etag == "abc123"
        assert result.size == 100

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_head_object_not_found(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio.stat_object.side_effect = _make_s3_error("NoSuchKey")
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ObjectNotFoundError, match="Object 'test.txt' not found"):
            client.head_object("test.txt")

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_head_object_empty_name_validation(self, mock_minio_class):
        mock_minio_class.return_value = Mock()
        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.head_object("")

    # ------------------------------------------------------------------
    # object_exists
    # ------------------------------------------------------------------

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_object_exists_true(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio.stat_object.return_value = Mock()
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        assert client.object_exists("test.txt") is True

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_object_exists_false(self, mock_minio_class):
        mock_minio = Mock()
        mock_minio.stat_object.side_effect = _make_s3_error("NoSuchKey")
        mock_minio_class.return_value = mock_minio

        client = ObjectStoreClient(_make_factory())
        assert client.object_exists("test.txt") is False

    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_object_exists_empty_name_validation(self, mock_minio_class):
        mock_minio_class.return_value = Mock()
        client = ObjectStoreClient(_make_factory())

        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.object_exists("")
