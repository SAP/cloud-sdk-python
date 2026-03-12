"""Tests for data models."""

from datetime import datetime
import pytest

from sap_cloud_sdk.objectstore._models import ObjectStoreBindingData, ObjectMetadata


class TestObjectStoreBindingData:

    def test_empty_initialization(self):
        config = ObjectStoreBindingData()
        assert config.access_key_id == ""
        assert config.secret_access_key == ""
        assert config.bucket == ""
        assert config.host == ""

    def test_field_assignment(self):
        config = ObjectStoreBindingData(
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket="test-bucket", 
            host="localhost:9000"
        )
        assert config.access_key_id == "test_key"
        assert config.secret_access_key == "test_secret"
        assert config.bucket == "test-bucket"
        assert config.host == "localhost:9000"

    def test_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(ObjectStoreBindingData)

    def test_mutable_fields(self):
        config = ObjectStoreBindingData()
        config.access_key_id = "new_key"
        config.secret_access_key = "new_secret"
        assert config.access_key_id == "new_key"
        assert config.secret_access_key == "new_secret"


class TestObjectMetadata:

    def test_creation_all_fields(self):
        test_time = datetime(2023, 1, 1, 12, 0, 0)
        metadata = ObjectMetadata(
            key="test.txt",
            last_modified=test_time,
            etag="abc123",
            size=100,
            storage_class="STANDARD",
            owner="test_owner"
        )
        assert metadata.key == "test.txt"
        assert metadata.last_modified == test_time
        assert metadata.etag == "abc123"
        assert metadata.size == 100
        assert metadata.storage_class == "STANDARD"
        assert metadata.owner == "test_owner"

    def test_creation_optional_fields_none(self):
        test_time = datetime(2023, 1, 1, 12, 0, 0)
        metadata = ObjectMetadata(
            key="test.txt",
            last_modified=test_time,
            etag="abc123",
            size=100
        )
        assert metadata.storage_class is None
        assert metadata.owner is None

    def test_frozen_dataclass(self):
        test_time = datetime(2023, 1, 1, 12, 0, 0)
        metadata = ObjectMetadata(
            key="test.txt",
            last_modified=test_time,
            etag="abc123",
            size=100
        )
        
        with pytest.raises(AttributeError):
            metadata.key = "new_key"  # ty: ignore[invalid-assignment]

    def test_is_frozen_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(ObjectMetadata)
        
        test_time = datetime(2023, 1, 1, 12, 0, 0)
        metadata = ObjectMetadata(
            key="test.txt",
            last_modified=test_time,
            etag="abc123",
            size=100
        )
        assert metadata.__dataclass_params__.frozen is True
