"""Tests for data models."""

from dataclasses import is_dataclass
from datetime import datetime

import pytest

from sap_cloud_sdk.objectstore._models import ObjectMetadata
from sap_cloud_sdk.objectstore.config import (
    AzureBindingData,
    GcsBindingData,
    S3BindingData,
)


class TestS3BindingData:

    def test_empty_initialization(self):
        config = S3BindingData()
        assert config.access_key_id == ""
        assert config.secret_access_key == ""
        assert config.bucket == ""
        assert config.host == ""

    def test_field_assignment(self):
        config = S3BindingData(
            access_key_id="test_key",
            secret_access_key="test_secret",
            bucket="test-bucket",
            host="localhost:9000",
        )
        assert config.access_key_id == "test_key"
        assert config.secret_access_key == "test_secret"
        assert config.bucket == "test-bucket"
        assert config.host == "localhost:9000"

    def test_is_dataclass(self):
        assert is_dataclass(S3BindingData)

    def test_mutable_fields(self):
        config = S3BindingData()
        config.access_key_id = "new_key"
        config.secret_access_key = "new_secret"
        assert config.access_key_id == "new_key"
        assert config.secret_access_key == "new_secret"


class TestAzureBindingData:

    def test_empty_initialization(self):
        config = AzureBindingData()
        assert config.account_name == ""
        assert config.container_name == ""
        assert config.container_uri == ""
        assert config.region == ""
        assert config.sas_token == ""

    def test_field_assignment(self):
        config = AzureBindingData(
            account_name="myaccount",
            container_name="mycontainer",
            container_uri="https://myaccount.blob.core.windows.net/mycontainer",
            region="westus",
            sas_token="sv=2020-08-04&ss=b",
        )
        assert config.account_name == "myaccount"
        assert config.container_name == "mycontainer"
        assert config.region == "westus"
        assert config.sas_token == "sv=2020-08-04&ss=b"

    def test_is_dataclass(self):
        assert is_dataclass(AzureBindingData)


class TestGcsBindingData:

    def test_empty_initialization(self):
        config = GcsBindingData()
        assert config.base64EncodedPrivateKeyData == ""
        assert config.projectId == ""
        assert config.bucket == ""
        assert config.key_algo == ""
        assert config.region == ""

    def test_field_assignment(self):
        config = GcsBindingData(
            base64EncodedPrivateKeyData="dGVzdA==",
            projectId="my-gcp-project",
            bucket="my-gcs-bucket",
            key_algo="RSA_2048",
            region="us-central1",
        )
        assert config.base64EncodedPrivateKeyData == "dGVzdA=="
        assert config.projectId == "my-gcp-project"
        assert config.bucket == "my-gcs-bucket"
        assert config.key_algo == "RSA_2048"
        assert config.region == "us-central1"

    def test_is_dataclass(self):
        assert is_dataclass(GcsBindingData)


class TestObjectMetadata:

    def test_creation_all_fields(self):
        test_time = datetime(2023, 1, 1, 12, 0, 0)
        metadata = ObjectMetadata(
            key="test.txt",
            last_modified=test_time,
            etag="abc123",
            size=100,
            storage_class="STANDARD",
            owner="test_owner",
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
            size=100,
        )
        assert metadata.storage_class is None
        assert metadata.owner is None

    def test_frozen_dataclass(self):
        test_time = datetime(2023, 1, 1, 12, 0, 0)
        metadata = ObjectMetadata(
            key="test.txt",
            last_modified=test_time,
            etag="abc123",
            size=100,
        )
        with pytest.raises(AttributeError):
            metadata.key = "new_key"  # ty: ignore[invalid-assignment]

    def test_is_frozen_dataclass(self):
        assert is_dataclass(ObjectMetadata)

        test_time = datetime(2023, 1, 1, 12, 0, 0)
        metadata = ObjectMetadata(
            key="test.txt",
            last_modified=test_time,
            etag="abc123",
            size=100,
        )
        assert metadata.__dataclass_params__.frozen is True
