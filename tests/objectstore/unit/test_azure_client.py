"""Tests for AzureClient object store backend."""

import io
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("azure.storage.blob")

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError  # noqa: E402
from azure.storage.blob import ContentSettings  # noqa: E402

from sap_cloud_sdk.objectstore._azure import AzureClient  # noqa: E402
from sap_cloud_sdk.objectstore.config import AzureConfig  # noqa: E402
from sap_cloud_sdk.objectstore.exceptions import (  # noqa: E402
    ObjectNotFoundError,
    ObjectOperationError,
)

_CREDS = AzureConfig(
    container_name="container",
    container_uri="https://account.blob.core.windows.net/container",
    sas_token="sv=2020",
)


def _make_client(mock_container):
    """Construct AzureClient with a patched container."""
    with patch.object(AzureClient, "_create_container_client", return_value=mock_container):
        return AzureClient(_CREDS)


class TestAzureClientPutObjectFromBytes:

    def test_put_object_from_bytes_happy_path(self):
        container = MagicMock()
        blob_client = MagicMock()
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        client.put_object_from_bytes("test.txt", b"hello", "text/plain")

        container.get_blob_client.assert_called_once_with("test.txt")
        blob_client.upload_blob.assert_called_once()
        call_kwargs = blob_client.upload_blob.call_args
        assert call_kwargs.kwargs.get("overwrite") is True
        cs = call_kwargs.kwargs.get("content_settings")
        assert isinstance(cs, ContentSettings)

    def test_put_object_from_bytes_empty_name_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.put_object_from_bytes("", b"data", "text/plain")

    def test_put_object_from_bytes_non_bytes_data_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="data must be bytes"):
            client.put_object_from_bytes("key", "not bytes", "text/plain")

    def test_put_object_from_bytes_empty_content_type_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="content_type must be a non-empty string"):
            client.put_object_from_bytes("key", b"data", "")


class TestAzureClientPutObject:

    def test_put_object_happy_path(self):
        container = MagicMock()
        blob_client = MagicMock()
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)
        stream = io.BytesIO(b"data")

        client.put_object("test.txt", stream, 4, "application/octet-stream")

        blob_client.upload_blob.assert_called_once()
        call_kwargs = blob_client.upload_blob.call_args
        assert call_kwargs.kwargs.get("length") == 4
        assert call_kwargs.kwargs.get("overwrite") is True

    def test_put_object_negative_size_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="size must be non-negative"):
            client.put_object("key", io.BytesIO(b""), -1, "text/plain")

    def test_put_object_invalid_stream_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="stream must be"):
            client.put_object("key", "not-a-stream", 0, "text/plain")


class TestAzureClientPutObjectFromFile:

    def test_put_object_from_file_empty_name_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.put_object_from_file("", "/path/file.txt", "text/plain")

    def test_put_object_from_file_empty_path_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="file_path must be a non-empty string"):
            client.put_object_from_file("key", "", "text/plain")

    def test_put_object_from_file_missing_file_raises(self):
        container = MagicMock()
        container.get_blob_client.return_value = MagicMock()
        client = _make_client(container)
        with pytest.raises(ObjectOperationError, match="File not found"):
            client.put_object_from_file("key", "/nonexistent/path.txt", "text/plain")


class TestAzureClientGetObject:

    def test_get_object_happy_path(self):
        container = MagicMock()
        blob_client = MagicMock()
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"test"
        blob_client.download_blob.return_value = mock_stream
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        result = client.get_object("test.txt")

        blob_client.download_blob.assert_called_once()
        assert result.read(4) == b"test"
        mock_stream.read.assert_called_once_with(4)

    def test_get_object_reader_close_is_idempotent(self):
        container = MagicMock()
        blob_client = MagicMock()
        mock_stream = MagicMock()
        blob_client.download_blob.return_value = mock_stream
        container.get_blob_client.return_value = blob_client
        reader = _make_client(container).get_object("test.txt")

        reader.close()
        reader.close()

        mock_stream.close.assert_not_called()
        with pytest.raises(ValueError, match="closed object reader"):
            reader.read()
        with pytest.raises(ValueError, match="closed object reader"):
            with reader:
                pass

    def test_get_object_reader_context_manager_closes_on_error(self):
        container = MagicMock()
        blob_client = MagicMock()
        mock_stream = MagicMock()
        blob_client.download_blob.return_value = mock_stream
        container.get_blob_client.return_value = blob_client
        reader = _make_client(container).get_object("test.txt")

        with pytest.raises(RuntimeError, match="boom"):
            with reader as entered:
                assert entered is reader
                raise RuntimeError("boom")

        with pytest.raises(ValueError, match="closed object reader"):
            reader.read()

    def test_get_object_not_found_via_resource_not_found_error(self):
        container = MagicMock()
        blob_client = MagicMock()
        blob_client.download_blob.side_effect = ResourceNotFoundError("not found")
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        with pytest.raises(ObjectNotFoundError, match="Object 'missing.txt' not found"):
            client.get_object("missing.txt")

    def test_get_object_not_found_via_http_404(self):
        container = MagicMock()
        blob_client = MagicMock()
        err = HttpResponseError("404")
        err.status_code = 404
        blob_client.download_blob.side_effect = err
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        with pytest.raises(ObjectNotFoundError):
            client.get_object("missing.txt")

    def test_get_object_empty_name_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.get_object("")


class TestAzureClientDeleteObject:

    def test_delete_object_happy_path(self):
        container = MagicMock()
        blob_client = MagicMock()
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        client.delete_object("test.txt")

        blob_client.delete_blob.assert_called_once()

    def test_delete_object_idempotent_swallows_resource_not_found(self):
        container = MagicMock()
        blob_client = MagicMock()
        blob_client.delete_blob.side_effect = ResourceNotFoundError("already gone")
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        # Should not raise
        client.delete_object("test.txt")

    def test_delete_object_empty_name_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.delete_object("")


class TestAzureClientListObjects:

    def test_list_objects_happy_path(self):
        container = MagicMock()
        blob1 = MagicMock()
        blob1.name = "prefix/file1.txt"
        blob1.last_modified = datetime(2023, 1, 1)
        blob1.etag = '"abc123"'
        blob1.size = 100
        blob1.blob_tier = None
        container.list_blobs.return_value = [blob1]
        client = _make_client(container)

        result = client.list_objects("prefix/")

        container.list_blobs.assert_called_once_with(name_starts_with="prefix/")
        assert len(result) == 1
        assert result[0].key == "prefix/file1.txt"
        assert result[0].etag == "abc123"  # quotes stripped
        assert result[0].size == 100
        assert result[0].owner is None
        assert result[0].storage_class is None

    def test_list_objects_with_blob_tier_sets_storage_class(self):
        container = MagicMock()
        blob1 = MagicMock()
        blob1.name = "file.txt"
        blob1.last_modified = datetime(2023, 1, 1)
        blob1.etag = "etag1"
        blob1.size = 50
        blob1.blob_tier = "Hot"
        container.list_blobs.return_value = [blob1]
        client = _make_client(container)

        result = client.list_objects("")

        assert result[0].storage_class == "Hot"

    def test_list_objects_invalid_prefix_type_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="prefix must be a string"):
            client.list_objects(123)


class TestAzureClientHeadObject:

    def test_head_object_happy_path(self):
        container = MagicMock()
        blob_client = MagicMock()
        props = MagicMock()
        props.last_modified = datetime(2023, 6, 15)
        props.etag = '"etag42"'
        props.size = 512
        props.blob_tier = None
        blob_client.get_blob_properties.return_value = props
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        result = client.head_object("file.txt")

        assert result.key == "file.txt"
        assert result.etag == "etag42"
        assert result.size == 512
        assert result.owner is None
        assert result.storage_class is None

    def test_head_object_not_found_raises_object_not_found_error(self):
        container = MagicMock()
        blob_client = MagicMock()
        blob_client.get_blob_properties.side_effect = ResourceNotFoundError("gone")
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        with pytest.raises(ObjectNotFoundError):
            client.head_object("missing.txt")

    def test_head_object_empty_name_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.head_object("")


class TestCreateContainerClient:
    """Test AzureClient._create_container_client in isolation (mirrors TestCreateStorageClient in GCS)."""

    def test_build_container_client_calls_from_container_url_with_correct_args(self):
        from unittest.mock import sentinel

        cfg = AzureConfig(
            container_name="container",
            container_uri="https://account.blob.core.windows.net/container",
            sas_token="sv=2020",
        )

        with patch(
            "azure.storage.blob.ContainerClient.from_container_url",
            return_value=sentinel.container_client,
        ) as mock_from_url:
            instance = object.__new__(AzureClient)
            result = instance._create_container_client(cfg)

        mock_from_url.assert_called_once_with(
            cfg.container_uri, credential=cfg.sas_token
        )
        assert result is sentinel.container_client

    def test_import_error_raises_client_creation_error(self):
        from sap_cloud_sdk.objectstore.exceptions import ClientCreationError

        cfg = AzureConfig(
            container_name="container",
            container_uri="https://account.blob.core.windows.net/container",
            sas_token="sv=2020",
        )

        # Simulate the ImportError branch by patching ContainerClient.from_container_url
        # to raise ImportError (which the method catches and re-wraps).
        with patch(
            "azure.storage.blob.ContainerClient.from_container_url",
            side_effect=ImportError("azure-storage-blob not installed"),
        ):
            instance = object.__new__(AzureClient)
            with pytest.raises(ClientCreationError, match="sap-cloud-sdk\\[azure\\]"):
                instance._create_container_client(cfg)


class TestAzureClientObjectExists:

    def test_object_exists_returns_true_when_present(self):
        container = MagicMock()
        blob_client = MagicMock()
        props = MagicMock()
        props.last_modified = datetime(2023, 1, 1)
        props.etag = "etag"
        props.size = 1
        props.blob_tier = None
        blob_client.get_blob_properties.return_value = props
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        assert client.object_exists("file.txt") is True

    def test_object_exists_returns_false_when_not_found(self):
        container = MagicMock()
        blob_client = MagicMock()
        blob_client.get_blob_properties.side_effect = ResourceNotFoundError("gone")
        container.get_blob_client.return_value = blob_client
        client = _make_client(container)

        assert client.object_exists("missing.txt") is False

    def test_object_exists_empty_name_raises(self):
        client = _make_client(MagicMock())
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.object_exists("")
