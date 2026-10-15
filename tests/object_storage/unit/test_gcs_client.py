"""Unit tests for the Google Cloud Storage backend (``object_storage._gcs``)."""

import base64
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from google.api_core.exceptions import Forbidden
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
    return GcsClient(lambda: CONFIG)


@pytest.fixture
def bucket(gcs):
    return gcs[1]


class TestConstruction:
    def test_valid_key_builds_client_with_project(self, gcs):
        storage, _ = gcs
        GcsClient(lambda: CONFIG)
        assert storage.Client.call_args.kwargs["project"] == "p"

    def test_bad_base64_raises_client_creation_error(self):
        with patch(STORAGE), patch(SERVICE_ACCOUNT):
            cfg = GcsConfig(
                base64_encoded_private_key_data="!!not-base64!!",
                project_id="p",
                bucket="b",
            )
            with pytest.raises(ClientCreationError, match="Failed to create Google"):
                GcsClient(lambda: cfg)

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
                GcsClient(lambda: cfg)


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


class _RotatingFactory:
    """Config factory stub with controllable rotation signalling."""

    def __init__(self, config: GcsConfig, *, changed: bool = False) -> None:
        self._config = config
        self.changed = changed
        self.calls = 0

    def __call__(self) -> GcsConfig:
        self.calls += 1
        return self._config

    def has_changed(self) -> bool:
        return self.changed


def _meta_blob() -> Mock:
    blob = Mock(updated=None, etag="", size=0, storage_class=None)
    blob.name = "k"
    return blob


class TestRotation:
    def test_proactive_rebuild_when_secret_changed(self):
        with patch(STORAGE) as storage, patch(SERVICE_ACCOUNT):
            original, rotated = Mock(), Mock()
            rotated.bucket.return_value.blob.return_value = _meta_blob()
            storage.Client.side_effect = [original, rotated]
            factory = _RotatingFactory(CONFIG)
            client = GcsClient(factory)
            assert factory.calls == 1
            assert client._bucket is original.bucket.return_value

            factory.changed = True
            client.head_object("k")

            assert factory.calls == 2  # re-read on rotation
            assert storage.Client.call_count == 2  # storage client rebuilt
            assert client._bucket is rotated.bucket.return_value  # holds new bucket

    def test_reactive_retry_once_on_credential_error(self):
        with patch(STORAGE) as storage, patch(SERVICE_ACCOUNT):
            first, rebuilt = Mock(), Mock()
            first_blob = Mock()
            first_blob.reload.side_effect = Forbidden("rejected")
            first.bucket.return_value.blob.return_value = first_blob
            rebuilt.bucket.return_value.blob.return_value = _meta_blob()
            storage.Client.side_effect = [first, rebuilt]

            factory = _RotatingFactory(CONFIG)
            client = GcsClient(factory)
            client.head_object("k")

            assert factory.calls == 2  # refreshed after rejection
            rebuilt.bucket.return_value.blob.return_value.reload.assert_called_once()
            assert client._bucket is rebuilt.bucket.return_value  # holds new bucket

    def test_no_rebuild_when_secret_unchanged(self, gcs):
        storage, bucket = gcs
        bucket.blob.return_value = _meta_blob()
        factory = _RotatingFactory(CONFIG, changed=False)
        client = GcsClient(factory)

        client.head_object("k")
        client.head_object("k")

        assert factory.calls == 1  # only the initial read

    def test_static_factory_never_tracks_rotation(self, gcs):
        storage, bucket = gcs
        bucket.blob.return_value = _meta_blob()
        client = GcsClient(lambda: CONFIG)  # no has_changed attribute

        client.head_object("k")
        client.head_object("k")

        assert bucket.blob.return_value.reload.call_count == 2
