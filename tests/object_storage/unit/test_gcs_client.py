"""Unit tests for the Google Cloud Storage backend (``object_storage._gcs``)."""

import base64
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from google.cloud.exceptions import NotFound

from sap_cloud_sdk.object_storage._gcs import GcsClient
from sap_cloud_sdk.object_storage.config import GcsConfig
from sap_cloud_sdk.object_storage.exceptions import (
    ClientCreationError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)

STORAGE = "sap_cloud_sdk.object_storage._gcs.storage"
SERVICE_ACCOUNT = "sap_cloud_sdk.object_storage._gcs.service_account"

VALID_KEY = base64.b64encode(b"{}").decode()
CONFIG = GcsConfig(
    base64_encoded_private_key_data=VALID_KEY, project_id="p", bucket="b"
)


@pytest.fixture
def gcs():
    """Patch both GCS seams; yield (storage_module, bucket_mock)."""
    with patch(STORAGE) as storage, patch(SERVICE_ACCOUNT):
        bucket = storage.Client.return_value.bucket.return_value
        yield storage, bucket


@pytest.fixture
def client(gcs):
    return GcsClient(CONFIG)


@pytest.fixture
def bucket(gcs):
    return gcs[1]


class TestConstruction:
    def test_valid_key_builds_client_with_project(self, gcs):
        storage, _ = gcs
        GcsClient(CONFIG)
        assert storage.Client.call_args.kwargs["project"] == "p"

    def test_bad_base64_raises_client_creation_error(self):
        with patch(STORAGE), patch(SERVICE_ACCOUNT):
            cfg = GcsConfig(
                base64_encoded_private_key_data="!!not-base64!!",
                project_id="p",
                bucket="b",
            )
            with pytest.raises(ClientCreationError, match="Failed to create Google"):
                GcsClient(cfg)

    def test_bad_json_raises_client_creation_error(self):
        with patch(STORAGE), patch(SERVICE_ACCOUNT):
            cfg = GcsConfig(
                base64_encoded_private_key_data=base64.b64encode(
                    b"not json"
                ).decode(),
                project_id="p",
                bucket="b",
            )
            with pytest.raises(ClientCreationError, match="Failed to create Google"):
                GcsClient(cfg)


class TestOperations:
    def test_put_from_bytes_uploads(self, client, bucket):
        client.put_object_from_bytes("k", b"data", "text/plain")
        bucket.blob.return_value.upload_from_string.assert_called_once()

    def test_put_failure_becomes_operation_error(self, client, bucket):
        bucket.blob.return_value.upload_from_string.side_effect = Exception("boom")
        with pytest.raises(ObjectOperationError, match="Failed to upload"):
            client.put_object_from_bytes("k", b"data", "text/plain")

    def test_get_reloads_then_opens_stream(self, client, bucket):
        blob = bucket.blob.return_value
        assert client.get_object("k") is blob.open.return_value
        blob.reload.assert_called_once()
        blob.open.assert_called_once_with("rb")

    def test_get_missing_object_becomes_not_found(self, client, bucket):
        bucket.blob.return_value.reload.side_effect = NotFound("missing")
        bucket.exists.return_value = True
        with pytest.raises(ObjectNotFoundError):
            client.get_object("k")

    def test_get_missing_bucket_becomes_operation_error(self, client, bucket):
        bucket.blob.return_value.reload.side_effect = NotFound("missing")
        bucket.exists.return_value = False
        with pytest.raises(ObjectOperationError):
            client.get_object("k")

    def test_delete_swallows_not_found_when_bucket_exists(self, client, bucket):
        bucket.blob.return_value.delete.side_effect = NotFound("missing")
        bucket.exists.return_value = True
        client.delete_object("k")

    def test_delete_other_error_becomes_operation_error(self, client, bucket):
        bucket.blob.return_value.delete.side_effect = Exception("boom")
        with pytest.raises(ObjectOperationError):
            client.delete_object("k")

    def test_list_maps_metadata_and_strips_etag(self, client, gcs):
        storage, _ = gcs
        blob = Mock(
            updated=datetime(2024, 1, 1, tzinfo=UTC),
            etag='"abc"',
            size=5,
            storage_class="STANDARD",
        )
        blob.name = "k"
        storage.Client.return_value.list_blobs.return_value = [blob]
        result = client.list_objects("p/")
        assert result[0].key == "k"
        assert result[0].etag == "abc"

    def test_list_error_becomes_list_objects_error(self, client, gcs):
        storage, _ = gcs
        storage.Client.return_value.list_blobs.side_effect = Exception("boom")
        with pytest.raises(ListObjectsError):
            client.list_objects("p/")

    def test_head_returns_metadata(self, client, bucket):
        blob = bucket.blob.return_value
        blob.name = "k"
        blob.updated = datetime(2024, 1, 1, tzinfo=UTC)
        blob.etag = '"xyz"'
        blob.size = 9
        blob.storage_class = "STANDARD"
        meta = client.head_object("k")
        assert meta.size == 9
        assert meta.etag == "xyz"

    def test_head_missing_becomes_not_found(self, client, bucket):
        bucket.blob.return_value.reload.side_effect = NotFound("missing")
        bucket.exists.return_value = True
        with pytest.raises(ObjectNotFoundError):
            client.head_object("k")

    def test_exists_true_and_false(self, client, bucket):
        blob = bucket.blob.return_value
        blob.name = "k"
        blob.updated = None
        blob.etag = ""
        blob.size = 0
        blob.storage_class = None
        assert client.object_exists("k") is True

        blob.reload.side_effect = NotFound("missing")
        bucket.exists.return_value = True
        assert client.object_exists("k") is False

    def test_validation_error_is_valueerror(self, client):
        with pytest.raises(ValueError):
            client.get_object("")
