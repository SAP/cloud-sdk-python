"""Tests for S3 client functionality."""

import io
import os
from datetime import datetime
from http.client import HTTPResponse
from unittest.mock import Mock, patch, mock_open
import pytest
from minio.error import S3Error

from cloud_sdk_python.objectstore._s3 import ObjectStoreClient
from cloud_sdk_python.objectstore._models import ObjectStoreBindingData, ObjectMetadata
from cloud_sdk_python.objectstore.exceptions import (
    ClientCreationError, ObjectOperationError, ObjectNotFoundError, ListObjectsError
)


@patch('cloud_sdk_python.objectstore._s3.create_auditlog_client')
class TestObjectStoreClient:

    def setup_method(self):
        self.creds = ObjectStoreBindingData(
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket="test-bucket",
            host="s3.amazonaws.com"
        )

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_client_creation_ssl_enabled(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds, disable_ssl=False)
        
        mock_minio_class.assert_called_once_with(
            endpoint="s3.amazonaws.com",
            access_key="test_key",
            secret_key="test_secret",
            secure=True
        )
        assert client._minio_client == mock_minio

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_client_creation_ssl_disabled(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds, disable_ssl=True)
        
        mock_minio_class.assert_called_once_with(
            endpoint="s3.amazonaws.com",
            access_key="test_key",
            secret_key="test_secret",
            secure=False
        )

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_client_creation_failure(self, mock_minio_class, mock_audit_client):
        mock_minio_class.side_effect = Exception("Connection failed")
        mock_audit_client.return_value = Mock()
        
        with pytest.raises(ClientCreationError, match="Failed to create MinIO client"):
            ObjectStoreClient(self.creds)

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_put_object_from_bytes_success(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        test_data = b"Hello, World!"
        
        client.put_object_from_bytes("test.txt", test_data, "text/plain")
        
        mock_minio.put_object.assert_called_once()
        call_args = mock_minio.put_object.call_args
        assert call_args.kwargs['bucket_name'] == 'test-bucket'
        assert call_args.kwargs['object_name'] == 'test.txt'
        assert call_args.kwargs['length'] == len(test_data)
        assert call_args.kwargs['content_type'] == 'text/plain'
        assert isinstance(call_args.kwargs['data'], io.BytesIO)

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_put_object_from_bytes_validation(self, mock_minio_class, mock_audit_client):
        mock_minio_class.return_value = Mock()
        mock_audit_client.return_value = Mock()
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.put_object_from_bytes("", b"data", "text/plain")
        
        with pytest.raises(ValueError, match="data must be bytes"):
            client.put_object_from_bytes("test.txt", "not bytes", "text/plain")
        
        with pytest.raises(ValueError, match="content_type must be a non-empty string"):
            client.put_object_from_bytes("test.txt", b"data", "")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_put_object_from_bytes_s3_error(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        s3_error = S3Error("AccessDenied", "Access denied", "test.txt", "123", "456", Mock())
        mock_minio.put_object.side_effect = s3_error
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ObjectOperationError, match="Failed to upload object"):
            client.put_object_from_bytes("test.txt", b"data", "text/plain")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_put_object_from_stream_success(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        stream = io.BytesIO(b"stream data")
        
        client.put_object("test.txt", stream, 11, "text/plain")
        
        # Note: The implementation reads the stream and creates a new BytesIO
        mock_minio.put_object.assert_called_once()
        call_args = mock_minio.put_object.call_args
        assert call_args.kwargs['bucket_name'] == 'test-bucket'
        assert call_args.kwargs['object_name'] == 'test.txt'
        assert call_args.kwargs['length'] == 11
        assert call_args.kwargs['content_type'] == 'text/plain'

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_put_object_validation(self, mock_minio_class, mock_audit_client):
        mock_minio_class.return_value = Mock()
        mock_audit_client.return_value = Mock()
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ValueError, match="size must be non-negative"):
            client.put_object("test.txt", io.BytesIO(b"data"), -1, "text/plain")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    @patch('builtins.open', new_callable=mock_open, read_data=b"file content")
    @patch('os.path.isfile', return_value=True)
    @patch('os.path.getsize', return_value=12)
    def test_put_object_from_file_success(self, mock_getsize, mock_isfile, mock_file, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        client.put_object_from_file("test.txt", "/path/to/file.txt", "text/plain")
        
        mock_isfile.assert_called_once_with("/path/to/file.txt")
        mock_getsize.assert_called_once_with("/path/to/file.txt")
        mock_minio.put_object.assert_called_once()

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    @patch('builtins.open', new_callable=mock_open, read_data=b"file content")
    @patch('os.path.isfile', return_value=False)
    def test_put_object_from_file_not_found(self, mock_isfile, mock_file, mock_minio_class, mock_audit_client):
        mock_minio_class.return_value = Mock()
        mock_audit_client.return_value = Mock()
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ObjectOperationError, match="File not found"):
            client.put_object_from_file("test.txt", "/nonexistent.txt", "text/plain")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_get_object_success(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        mock_response = Mock(spec=HTTPResponse)
        mock_minio.get_object.return_value = mock_response
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        result = client.get_object("test.txt")
        
        mock_minio.get_object.assert_called_once_with(
            bucket_name='test-bucket',
            object_name='test.txt'
        )
        assert result == mock_response

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_get_object_not_found(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        s3_error = S3Error("NoSuchKey", "Key not found", "test.txt", "123", "456", Mock())
        mock_minio.get_object.side_effect = s3_error
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ObjectNotFoundError, match="Object 'test.txt' not found"):
            client.get_object("test.txt")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_delete_object_success(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        client.delete_object("test.txt")
        
        mock_minio.remove_object.assert_called_once_with(
            bucket_name='test-bucket',
            object_name='test.txt'
        )

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_delete_object_not_found_ignored(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        s3_error = S3Error("NoSuchKey", "Key not found", "test.txt", "123", "456", Mock())
        mock_minio.remove_object.side_effect = s3_error
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        client.delete_object("test.txt")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_list_objects_success(self, mock_minio_class, mock_audit_client):
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
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        result = client.list_objects("prefix/")
        
        mock_minio.list_objects.assert_called_once_with(
            bucket_name='test-bucket',
            prefix='prefix/'
        )
        
        assert len(result) == 1
        assert result[0].key == "prefix/file1.txt"
        assert result[0].etag == '"abc123"'

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_list_objects_s3_error(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        s3_error = S3Error("AccessDenied", "Access denied", "", "123", "456", Mock())
        mock_minio.list_objects.side_effect = s3_error
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ListObjectsError, match="Failed to list objects"):
            client.list_objects("prefix/")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_head_object_success(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        
        mock_stat = Mock()
        mock_stat.last_modified = datetime(2023, 1, 1, 12, 0, 0)
        mock_stat.etag = '"abc123"'
        mock_stat.size = 100
        
        mock_minio.stat_object.return_value = mock_stat
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        result = client.head_object("test.txt")
        
        mock_minio.stat_object.assert_called_once_with(
            bucket_name='test-bucket',
            object_name='test.txt'
        )
        
        assert result.key == "test.txt"
        assert result.etag == "abc123"
        assert result.size == 100

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_head_object_not_found(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        s3_error = S3Error("NoSuchKey", "Key not found", "test.txt", "123", "456", Mock())
        mock_minio.stat_object.side_effect = s3_error
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ObjectNotFoundError, match="Object 'test.txt' not found"):
            client.head_object("test.txt")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_object_exists_true(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        mock_minio.stat_object.return_value = Mock()
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        result = client.object_exists("test.txt")
        
        assert result is True

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_object_exists_false(self, mock_minio_class, mock_audit_client):
        mock_minio = Mock()
        s3_error = S3Error("NoSuchKey", "Key not found", "test.txt", "123", "456", Mock())
        mock_minio.stat_object.side_effect = s3_error
        mock_minio_class.return_value = mock_minio
        mock_audit_client.return_value = Mock()
        
        client = ObjectStoreClient(self.creds)
        result = client.object_exists("test.txt")
        
        assert result is False

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_get_object_empty_name_validation(self, mock_minio_class, mock_audit_client):
        mock_minio_class.return_value = Mock()
        mock_audit_client.return_value = Mock()
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.get_object("")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_delete_object_empty_name_validation(self, mock_minio_class, mock_audit_client):
        mock_minio_class.return_value = Mock()
        mock_audit_client.return_value = Mock()
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.delete_object("")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_head_object_empty_name_validation(self, mock_minio_class, mock_audit_client):
        mock_minio_class.return_value = Mock()
        mock_audit_client.return_value = Mock()
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.head_object("")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_object_exists_empty_name_validation(self, mock_minio_class, mock_audit_client):
        mock_minio_class.return_value = Mock()
        mock_audit_client.return_value = Mock()
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            client.object_exists("")

    @patch('cloud_sdk_python.objectstore._s3.Minio')
    def test_list_objects_prefix_validation(self, mock_minio_class, mock_audit_client):
        mock_minio_class.return_value = Mock()
        mock_audit_client.return_value = Mock()
        client = ObjectStoreClient(self.creds)
        
        with pytest.raises(ValueError, match="prefix must be a string"):
            client.list_objects(123)
