"""Tests for GcsClient object store backend."""

import base64
import io
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("google.cloud.storage")

from google.cloud.exceptions import NotFound  # noqa: E402

from sap_cloud_sdk.objectstore._gcs import GcsClient  # noqa: E402
from sap_cloud_sdk.objectstore.config import GcsConfig  # noqa: E402
from sap_cloud_sdk.objectstore.exceptions import (  # noqa: E402
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)

_CREDS = GcsConfig(
    base64_encoded_private_key_data="dGVzdA==",
    project_id="my-project",
    bucket="my-bucket",
)


def _make_client():
    """Return (GcsClient, mock_gcs_client, mock_bucket) with patched builder."""
    mock_gcs = MagicMock()
    mock_bucket = MagicMock()
    mock_gcs.bucket.return_value = mock_bucket
    with patch.object(GcsClient, "_create_storage_client", return_value=mock_gcs):
        client = GcsClient(_CREDS)
    return client, mock_gcs, mock_bucket


class TestGcsClientPutObjectFromBytes:

    def test_put_object_from_bytes_happy_path(self):
        client, _, bucket = _make_client()
        mock_blob = MagicMock()
        bucket.blob.return_value = mock_blob

        client.put_object_from_bytes("test.txt", b"hello", "text/plain")

        bucket.blob.assert_called_with("test.txt")
        mock_blob.upload_from_string.assert_called_once_with(
            b"hello", content_type="text/plain"
        )

    def test_put_object_from_bytes_empty_name_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.put_object_from_bytes("", b"data", "text/plain")

    def test_put_object_from_bytes_non_bytes_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="data must be bytes"):
            client.put_object_from_bytes("key", "not bytes", "text/plain")

    def test_put_object_from_bytes_empty_content_type_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="content_type must be a non-empty string"):
            client.put_object_from_bytes("key", b"data", "")

    def test_put_object_from_bytes_network_failure_is_wrapped(self):
        client, _, bucket = _make_client()
        bucket.blob.return_value.upload_from_string.side_effect = ConnectionError(
            "network unavailable"
        )

        with pytest.raises(ObjectOperationError, match="network unavailable"):
            client.put_object_from_bytes("key", b"data", "text/plain")


class TestGcsClientPutObject:

    def test_put_object_happy_path(self):
        client, _, bucket = _make_client()
        mock_blob = MagicMock()
        bucket.blob.return_value = mock_blob
        stream = io.BytesIO(b"data")

        client.put_object("test.txt", stream, 4, "application/octet-stream")

        mock_blob.upload_from_file.assert_called_once_with(
            stream, size=4, content_type="application/octet-stream"
        )

    def test_put_object_negative_size_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="size must be non-negative"):
            client.put_object("key", io.BytesIO(b""), -1, "text/plain")

    def test_put_object_invalid_stream_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="stream must be"):
            client.put_object("key", "not-a-stream", 0, "text/plain")


class TestGcsClientPutObjectFromFile:

    def test_put_object_from_file_empty_name_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.put_object_from_file("", "/path/to/file.txt", "text/plain")

    def test_put_object_from_file_empty_path_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="file_path must be a non-empty string"):
            client.put_object_from_file("key", "", "text/plain")

    def test_put_object_from_file_missing_file_raises(self):
        client, _, bucket = _make_client()
        bucket.blob.return_value = MagicMock()
        with pytest.raises(ObjectOperationError, match="File not found"):
            client.put_object_from_file("key", "/nonexistent/path.txt", "text/plain")


class TestGcsClientGetObject:

    def test_get_object_happy_path(self):
        client, _, bucket = _make_client()
        mock_blob = MagicMock()
        mock_stream = MagicMock()
        mock_blob.open.return_value = mock_stream
        bucket.blob.return_value = mock_blob

        result = client.get_object("test.txt")

        mock_blob.reload.assert_called_once()
        mock_blob.open.assert_called_once_with("rb")
        assert result is mock_stream

    def test_get_object_not_found_raises_object_not_found_error(self):
        client, _, bucket = _make_client()
        mock_blob = MagicMock()
        mock_blob.reload.side_effect = NotFound("not found")
        bucket.blob.return_value = mock_blob

        with pytest.raises(ObjectNotFoundError, match="Object 'missing.txt' not found"):
            client.get_object("missing.txt")

    def test_get_object_empty_name_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.get_object("")


class TestGcsClientDeleteObject:

    def test_delete_object_happy_path(self):
        client, _, bucket = _make_client()
        mock_blob = MagicMock()
        bucket.blob.return_value = mock_blob

        client.delete_object("test.txt")

        mock_blob.delete.assert_called_once()

    def test_delete_object_idempotent_swallows_not_found(self):
        client, _, bucket = _make_client()
        mock_blob = MagicMock()
        mock_blob.delete.side_effect = NotFound("gone")
        bucket.blob.return_value = mock_blob

        # Should not raise
        client.delete_object("test.txt")

    def test_delete_object_empty_name_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.delete_object("")


class TestGcsClientListObjects:

    def test_list_objects_happy_path(self):
        client, gcs_client, bucket = _make_client()
        mock_blob = MagicMock()
        mock_blob.name = "prefix/file1.txt"
        mock_blob.updated = datetime(2023, 1, 1)
        mock_blob.etag = '"abc123"'
        mock_blob.size = 200
        mock_blob.storage_class = "STANDARD"
        gcs_client.list_blobs.return_value = [mock_blob]

        result = client.list_objects("prefix/")

        gcs_client.list_blobs.assert_called_once_with(bucket, prefix="prefix/")
        assert len(result) == 1
        assert result[0].key == "prefix/file1.txt"
        assert result[0].etag == "abc123"  # quotes stripped
        assert result[0].size == 200
        assert result[0].storage_class == "STANDARD"
        assert result[0].owner is None

    def test_list_objects_empty_prefix_allowed(self):
        client, gcs_client, bucket = _make_client()
        gcs_client.list_blobs.return_value = []
        result = client.list_objects("")
        assert result == []

    def test_list_objects_invalid_prefix_type_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="prefix must be a string"):
            client.list_objects(42)

    def test_list_objects_network_failure_is_wrapped(self):
        client, gcs_client, _ = _make_client()
        gcs_client.list_blobs.side_effect = ConnectionError("network unavailable")

        with pytest.raises(ListObjectsError, match="network unavailable"):
            client.list_objects("prefix/")


class TestGcsClientHeadObject:

    def test_head_object_happy_path(self):
        client, _, bucket = _make_client()
        mock_blob = MagicMock()
        mock_blob.name = "file.txt"
        mock_blob.updated = datetime(2023, 6, 15)
        mock_blob.etag = '"etag99"'
        mock_blob.size = 1024
        mock_blob.storage_class = "NEARLINE"
        bucket.get_blob.return_value = mock_blob

        result = client.head_object("file.txt")

        bucket.get_blob.assert_called_once_with("file.txt")
        assert result.key == "file.txt"
        assert result.etag == "etag99"
        assert result.size == 1024
        assert result.storage_class == "NEARLINE"
        assert result.owner is None

    def test_head_object_none_blob_raises_object_not_found_error(self):
        client, _, bucket = _make_client()
        bucket.get_blob.return_value = None

        with pytest.raises(ObjectNotFoundError, match="Object 'missing.txt' not found"):
            client.head_object("missing.txt")

    def test_head_object_empty_name_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.head_object("")


class TestGcsClientObjectExists:

    def test_object_exists_returns_true_when_present(self):
        client, _, bucket = _make_client()
        mock_blob = MagicMock()
        mock_blob.name = "file.txt"
        mock_blob.updated = datetime(2023, 1, 1)
        mock_blob.etag = "etag"
        mock_blob.size = 1
        mock_blob.storage_class = None
        bucket.get_blob.return_value = mock_blob

        assert client.object_exists("file.txt") is True

    def test_object_exists_returns_false_when_not_found(self):
        client, _, bucket = _make_client()
        bucket.get_blob.return_value = None

        assert client.object_exists("missing.txt") is False

    def test_object_exists_empty_name_raises(self):
        client, _, _ = _make_client()
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.object_exists("")

    def test_object_exists_network_failure_is_wrapped(self):
        client, _, bucket = _make_client()
        bucket.get_blob.side_effect = ConnectionError("network unavailable")

        with pytest.raises(ObjectOperationError, match="network unavailable"):
            client.object_exists("key")


class TestCreateStorageClient:
    """Test the GcsClient._create_storage_client credential transform in isolation."""

    def test_build_gcs_client_decodes_base64_and_passes_to_credentials(self):
        service_account_info = {
            "type": "service_account",
            "project_id": "my-project",
            "private_key_id": "key-id",
        }
        encoded = base64.b64encode(
            json.dumps(service_account_info).encode()
        ).decode()
        cfg = GcsConfig(
            base64_encoded_private_key_data=encoded,
            project_id="my-project",
            bucket="my-bucket",
        )

        mock_creds = MagicMock()
        mock_storage_client = MagicMock()

        with patch(
            "google.oauth2.service_account.Credentials.from_service_account_info",
            return_value=mock_creds,
        ) as mock_from_info, patch(
            "google.cloud.storage.Client",
            return_value=mock_storage_client,
        ) as mock_client_class:
            instance = object.__new__(GcsClient)
            result = instance._create_storage_client(cfg)

        mock_from_info.assert_called_once_with(service_account_info)
        mock_client_class.assert_called_once_with(
            project="my-project", credentials=mock_creds
        )
        assert result is mock_storage_client
