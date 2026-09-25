"""Unit tests for the Azure Blob Storage backend (``object_storage._azure``)."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError

from sap_cloud_sdk.object_storage._azure import AzureClient, _AzureObjectReader
from sap_cloud_sdk.object_storage.config import AzureConfig
from sap_cloud_sdk.object_storage.exceptions import (
    ClientCreationError,
    ListObjectsError,
    ObjectNotFoundError,
    ObjectOperationError,
)

CONTAINER = "sap_cloud_sdk.object_storage._azure.ContainerClient"

CONFIG = AzureConfig(
    container_name="c",
    container_uri="https://acct.blob.core.windows.net/c",
    sas_token="sv=token",
)


def _blob_not_found() -> ResourceNotFoundError:
    exc = ResourceNotFoundError("missing")
    exc.error_code = "BlobNotFound"  # ty: ignore[unresolved-attribute]
    return exc


@pytest.fixture
def container():
    with patch(CONTAINER) as ctor:
        yield ctor.from_container_url.return_value


@pytest.fixture
def client(container):
    return AzureClient(lambda: CONFIG)


@pytest.fixture
def blob(container):
    return container.get_blob_client.return_value


class TestConstruction:
    def test_from_container_url_called_with_uri_and_token(self):
        with patch(CONTAINER) as ctor:
            AzureClient(lambda: CONFIG)
            ctor.from_container_url.assert_called_once_with(
                CONFIG.container_uri, credential=CONFIG.sas_token
            )

    def test_construction_failure_raises_client_creation_error(self):
        with patch(CONTAINER) as ctor:
            ctor.from_container_url.side_effect = Exception("boom")
            with pytest.raises(ClientCreationError, match="Failed to create Azure"):
                AzureClient(lambda: CONFIG)


class TestAzureObjectReader:
    def test_read_delegates_to_downloader(self):
        downloader = Mock()
        downloader.read.return_value = b"payload"
        reader = _AzureObjectReader(downloader)
        assert reader.read(4) == b"payload"
        downloader.read.assert_called_once_with(4)

    def test_close_is_idempotent(self):
        reader = _AzureObjectReader(Mock())
        reader.close()
        reader.close()

    def test_read_after_close_raises_valueerror(self):
        reader = _AzureObjectReader(Mock())
        reader.close()
        with pytest.raises(ValueError, match="closed object reader"):
            reader.read()

    def test_context_manager_closes_on_exit(self):
        reader = _AzureObjectReader(Mock())
        with reader as ctx:
            assert ctx is reader
        with pytest.raises(ValueError):
            reader.read()


class TestIsBlobNotFound:
    def test_true_for_resource_not_found_with_blobnotfound_code(self):
        assert AzureClient._is_blob_not_found(_blob_not_found()) is True

    def test_false_for_resource_not_found_other_code(self):
        exc = ResourceNotFoundError("missing")
        exc.error_code = "ContainerNotFound"  # ty: ignore[unresolved-attribute]
        assert AzureClient._is_blob_not_found(exc) is False

    def test_false_for_unrelated_exception(self):
        assert AzureClient._is_blob_not_found(RuntimeError()) is False


class TestOperations:
    def test_put_from_bytes_uploads_with_overwrite(self, client, blob):
        client.put_object_from_bytes("k", b"data", "text/plain")
        assert blob.upload_blob.call_args.kwargs["overwrite"] is True

    def test_put_failure_becomes_operation_error(self, client, blob):
        blob.upload_blob.side_effect = Exception("boom")
        with pytest.raises(ObjectOperationError, match="Failed to upload"):
            client.put_object_from_bytes("k", b"data", "text/plain")

    def test_get_returns_managed_reader(self, client, blob):
        reader = client.get_object("k")
        assert isinstance(reader, _AzureObjectReader)

    def test_get_missing_blob_becomes_not_found(self, client, blob):
        blob.download_blob.side_effect = _blob_not_found()
        with pytest.raises(ObjectNotFoundError):
            client.get_object("k")

    def test_get_other_error_becomes_operation_error(self, client, blob):
        blob.download_blob.side_effect = Exception("boom")
        with pytest.raises(ObjectOperationError):
            client.get_object("k")

    def test_delete_swallows_blob_not_found(self, client, blob):
        blob.delete_blob.side_effect = _blob_not_found()
        client.delete_object("k")

    def test_delete_other_error_becomes_operation_error(self, client, blob):
        blob.delete_blob.side_effect = Exception("boom")
        with pytest.raises(ObjectOperationError):
            client.delete_object("k")

    def test_list_maps_metadata_and_strips_etag(self, client, container):
        item = Mock(
            last_modified=datetime(2024, 1, 1, tzinfo=UTC),
            etag='"abc"',
            size=5,
            blob_tier="Hot",
        )
        item.name = "k"
        container.list_blobs.return_value = [item]
        result = client.list_objects("p/")
        assert result[0].key == "k"
        assert result[0].etag == "abc"
        assert result[0].storage_class == "Hot"

    def test_list_error_becomes_list_objects_error(self, client, container):
        container.list_blobs.side_effect = Exception("boom")
        with pytest.raises(ListObjectsError):
            client.list_objects("p/")

    def test_head_returns_metadata(self, client, blob):
        blob.get_blob_properties.return_value = Mock(
            last_modified=datetime(2024, 1, 1, tzinfo=UTC),
            etag='"xyz"',
            size=9,
            blob_tier="Cool",
        )
        meta = client.head_object("k")
        assert meta.size == 9
        assert meta.etag == "xyz"

    def test_head_missing_becomes_not_found(self, client, blob):
        blob.get_blob_properties.side_effect = _blob_not_found()
        with pytest.raises(ObjectNotFoundError):
            client.head_object("k")

    def test_exists_true_and_false(self, client, blob):
        blob.get_blob_properties.return_value = Mock(
            last_modified=None, etag="", size=0, blob_tier=None
        )
        assert client.object_exists("k") is True

        blob.get_blob_properties.side_effect = _blob_not_found()
        assert client.object_exists("k") is False

    def test_validation_error_is_valueerror(self, client):
        with pytest.raises(ValueError):
            client.get_object("")


class _RotatingFactory:
    """Config factory stub with controllable rotation signalling."""

    def __init__(self, config: AzureConfig, *, changed: bool = False) -> None:
        self._config = config
        self.changed = changed
        self.calls = 0

    def __call__(self) -> AzureConfig:
        self.calls += 1
        return self._config

    def has_changed(self) -> bool:
        return self.changed


def _props() -> Mock:
    return Mock(last_modified=None, etag="", size=0, blob_tier=None)


class TestRotation:
    def test_proactive_rebuild_when_secret_changed(self):
        with patch(CONTAINER) as ctor:
            original, rotated = Mock(), Mock()
            rotated.get_blob_client.return_value.get_blob_properties.return_value = (
                _props()
            )
            ctor.from_container_url.side_effect = [original, rotated]
            factory = _RotatingFactory(CONFIG)
            client = AzureClient(factory)
            assert factory.calls == 1
            assert client._container is original

            factory.changed = True
            client.head_object("k")

            assert factory.calls == 2  # re-read on rotation
            assert ctor.from_container_url.call_count == 2  # container rebuilt
            assert client._container is rotated  # holds the new container

    def test_reactive_retry_once_on_auth_error(self):
        with patch(CONTAINER) as ctor:
            first, rebuilt = Mock(), Mock()
            first.get_blob_client.return_value.get_blob_properties.side_effect = (
                ClientAuthenticationError("rejected")
            )
            rebuilt.get_blob_client.return_value.get_blob_properties.return_value = (
                _props()
            )
            ctor.from_container_url.side_effect = [first, rebuilt]

            factory = _RotatingFactory(CONFIG)
            client = AzureClient(factory)
            client.head_object("k")

            assert factory.calls == 2  # refreshed after rejection
            rebuilt.get_blob_client.return_value.get_blob_properties.assert_called_once()
            assert client._container is rebuilt  # holds the refreshed container

    def test_no_rebuild_when_secret_unchanged(self, container, blob):
        blob.get_blob_properties.return_value = _props()
        factory = _RotatingFactory(CONFIG, changed=False)
        client = AzureClient(factory)

        client.head_object("k")
        client.head_object("k")

        assert factory.calls == 1  # only the initial read

    def test_static_factory_never_tracks_rotation(self, container, blob):
        blob.get_blob_properties.return_value = _props()
        client = AzureClient(lambda: CONFIG)  # no has_changed attribute

        client.head_object("k")
        client.head_object("k")

        assert blob.get_blob_properties.call_count == 2
