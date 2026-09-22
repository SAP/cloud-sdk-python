"""Unit tests for the S3/MinIO backend (``object_storage._s3``)."""

import io
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from minio.error import S3Error

from sap_cloud_sdk.object_storage._s3 import S3Client
from sap_cloud_sdk.object_storage.config import S3Config
from sap_cloud_sdk.object_storage.exceptions import (
    ClientCreationError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)

MINIO = "sap_cloud_sdk.object_storage._s3.Minio"


def _s3_error(code: str) -> S3Error:
    """Build an S3Error for the installed minio (code is the first positional)."""
    return S3Error(code, "message", "resource", "request-id", "host-id", Mock())


def _config(
    *,
    access_key_id: str = "ak",
    secret_access_key: str = "sk",
    bucket: str = "bucket",
    host: str = "host",
    disable_ssl: bool = False,
) -> S3Config:
    return S3Config(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        bucket=bucket,
        host=host,
        disable_ssl=disable_ssl,
    )


@pytest.fixture
def minio_client():
    with patch(MINIO) as ctor:
        instance = ctor.return_value
        yield instance


@pytest.fixture
def client(minio_client):
    return S3Client(_config())


class TestConstruction:
    def test_secure_true_when_ssl_enabled(self):
        with patch(MINIO) as ctor:
            S3Client(_config(disable_ssl=False))
            assert ctor.call_args.kwargs["secure"] is True

    def test_secure_false_when_ssl_disabled(self):
        with patch(MINIO) as ctor:
            S3Client(_config(disable_ssl=True))
            assert ctor.call_args.kwargs["secure"] is False

    def test_regional_host_normalised(self):
        with patch(MINIO) as ctor:
            S3Client(_config(host="s3-eu-west-1.amazonaws.com"))
            assert ctor.call_args.kwargs["endpoint"] == "s3.eu-west-1.amazonaws.com"

    def test_construction_failure_raises_client_creation_error(self):
        with patch(MINIO, side_effect=Exception("boom")):
            with pytest.raises(ClientCreationError, match="Failed to create S3"):
                S3Client(_config())


class TestPutObject:
    def test_put_from_bytes_forwards_to_minio(self, client, minio_client):
        client.put_object_from_bytes("k", b"data", "text/plain")
        kwargs = minio_client.put_object.call_args.kwargs
        assert kwargs["bucket_name"] == "bucket"
        assert kwargs["object_name"] == "k"
        assert kwargs["length"] == 4

    def test_put_from_bytes_error_becomes_operation_error(self, client, minio_client):
        minio_client.put_object.side_effect = _s3_error("AccessDenied")
        with pytest.raises(ObjectOperationError, match="Failed to upload"):
            client.put_object_from_bytes("k", b"data", "text/plain")

    def test_put_object_stream_forwards_length(self, client, minio_client):
        client.put_object("k", io.BytesIO(b"xyz"), 3, "text/plain")
        assert minio_client.put_object.call_args.kwargs["length"] == 3

    def test_put_from_file_missing_file_raises_operation_error(self, client):
        with pytest.raises(ObjectOperationError, match="File not found"):
            client.put_object_from_file("k", "/no/such/file.txt", "text/plain")

    def test_put_validation_error_is_valueerror(self, client):
        with pytest.raises(ValueError):
            client.put_object_from_bytes("", b"data", "text/plain")


class TestGetObject:
    def test_get_returns_minio_response(self, client, minio_client):
        assert client.get_object("k") is minio_client.get_object.return_value

    def test_get_nosuchkey_becomes_not_found(self, client, minio_client):
        minio_client.get_object.side_effect = _s3_error("NoSuchKey")
        with pytest.raises(ObjectNotFoundError):
            client.get_object("k")

    def test_get_nosuchobject_becomes_not_found(self, client, minio_client):
        minio_client.get_object.side_effect = _s3_error("NoSuchObject")
        with pytest.raises(ObjectNotFoundError):
            client.get_object("k")

    def test_get_other_s3_error_becomes_operation_error(self, client, minio_client):
        minio_client.get_object.side_effect = _s3_error("AccessDenied")
        with pytest.raises(ObjectOperationError):
            client.get_object("k")


class TestDeleteObject:
    def test_delete_forwards_to_minio(self, client, minio_client):
        client.delete_object("k")
        minio_client.remove_object.assert_called_once()

    def test_delete_swallows_not_found_idempotently(self, client, minio_client):
        minio_client.remove_object.side_effect = _s3_error("NoSuchKey")
        client.delete_object("k")

    def test_delete_other_error_becomes_operation_error(self, client, minio_client):
        minio_client.remove_object.side_effect = _s3_error("AccessDenied")
        with pytest.raises(ObjectOperationError):
            client.delete_object("k")


class TestListObjects:
    def test_list_maps_metadata(self, client, minio_client):
        obj = Mock(
            object_name="k",
            last_modified=datetime(2024, 1, 1, tzinfo=UTC),
            etag='"abc"',
            size=7,
            storage_class="STANDARD",
            owner_name="owner",
        )
        minio_client.list_objects.return_value = [obj]
        result = client.list_objects("prefix/")
        assert result[0].key == "k"
        assert result[0].etag == "abc"
        assert result[0].owner == "owner"

    def test_list_missing_last_modified_falls_back_to_epoch_min(
        self, client, minio_client
    ):
        obj = Mock(
            object_name="k",
            last_modified=None,
            etag=None,
            size=0,
            storage_class=None,
            owner_name=None,
        )
        minio_client.list_objects.return_value = [obj]
        result = client.list_objects("")
        assert result[0].last_modified == datetime.min.replace(tzinfo=UTC)
        assert result[0].etag == ""

    def test_list_error_becomes_list_objects_error(self, client, minio_client):
        minio_client.list_objects.side_effect = _s3_error("AccessDenied")
        with pytest.raises(ListObjectsError):
            client.list_objects("prefix/")


class TestHeadObject:
    def test_head_strips_etag_quotes(self, client, minio_client):
        minio_client.stat_object.return_value = Mock(
            last_modified=datetime(2024, 1, 1, tzinfo=UTC), etag='"deadbeef"', size=10
        )
        assert client.head_object("k").etag == "deadbeef"

    def test_head_missing_fields_fall_back(self, client, minio_client):
        minio_client.stat_object.return_value = Mock(
            last_modified=None, etag=None, size=None
        )
        meta = client.head_object("k")
        assert meta.last_modified == datetime.min.replace(tzinfo=UTC)
        assert meta.size == 0

    def test_head_not_found_becomes_not_found(self, client, minio_client):
        minio_client.stat_object.side_effect = _s3_error("NoSuchKey")
        with pytest.raises(ObjectNotFoundError):
            client.head_object("k")

    def test_head_other_error_becomes_operation_error(self, client, minio_client):
        minio_client.stat_object.side_effect = _s3_error("AccessDenied")
        with pytest.raises(ObjectOperationError):
            client.head_object("k")


class TestObjectExists:
    def test_exists_true_when_head_succeeds(self, client, minio_client):
        minio_client.stat_object.return_value = Mock(
            last_modified=None, etag="", size=0
        )
        assert client.object_exists("k") is True

    def test_exists_false_when_not_found(self, client, minio_client):
        minio_client.stat_object.side_effect = _s3_error("NoSuchKey")
        assert client.object_exists("k") is False

    def test_exists_reraises_operation_error(self, client, minio_client):
        minio_client.stat_object.side_effect = _s3_error("AccessDenied")
        with pytest.raises(ObjectOperationError):
            client.object_exists("k")
