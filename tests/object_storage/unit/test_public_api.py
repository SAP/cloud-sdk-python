"""Unit tests for the public API surface of ``sap_cloud_sdk.object_storage``."""

import dataclasses
from datetime import datetime
from unittest.mock import patch

import sap_cloud_sdk.object_storage as object_storage
from sap_cloud_sdk.object_storage import (
    AzureConfig,
    GcsConfig,
    ObjectMetadata,
    ObjectReader,
    ObjectStoreClient,
    S3Config,
)
from sap_cloud_sdk.object_storage._s3 import S3Client


class TestPublicExports:
    def test_all_lists_every_documented_symbol_importable(self):
        for name in object_storage.__all__:
            assert hasattr(object_storage, name), name

    def test_all_matches_expected_names_exact_set(self):
        assert set(object_storage.__all__) == {
            "ObjectStoreClient",
            "ObjectReader",
            "S3Config",
            "AzureConfig",
            "GcsConfig",
            "ObjectMetadata",
            "create_client",
            "ObjectStoreError",
            "ConfigError",
            "ClientCreationError",
            "ObjectOperationError",
            "ObjectNotFoundError",
            "ListObjectsError",
        }


class TestObjectStoreClientProtocol:
    def test_isinstance_concrete_client_satisfies_protocol_true(self):
        with patch("sap_cloud_sdk.object_storage._s3.Minio"):
            client = S3Client(
                S3Config(
                    access_key_id="ak",
                    secret_access_key="sk",
                    bucket="b",
                    host="h",
                )
            )
        assert isinstance(client, ObjectStoreClient)

    def test_isinstance_bare_object_missing_methods_false(self):
        assert not isinstance(object(), ObjectStoreClient)


class TestObjectReaderProtocol:
    def test_reader_declares_managed_stream_shape(self):
        for method in ("read", "close", "__enter__", "__exit__"):
            assert hasattr(ObjectReader, method), method


class TestConfigRedaction:
    def test_s3config_repr_hides_secrets_keeps_public_fields(self):
        text = repr(
            S3Config(
                access_key_id="AK-secret",
                secret_access_key="SK-secret",
                bucket="my-bucket",
                host="my-host",
            )
        )
        assert "AK-secret" not in text
        assert "SK-secret" not in text
        assert "my-bucket" in text
        assert "my-host" in text

    def test_azureconfig_repr_hides_sas_token_keeps_public_fields(self):
        text = repr(
            AzureConfig(
                container_name="c",
                container_uri="https://acct.blob.core.windows.net/c",
                sas_token="sv=secret-token",
            )
        )
        assert "sv=secret-token" not in text
        assert "c" in text
        assert "acct.blob.core.windows.net" in text

    def test_gcsconfig_repr_hides_private_key_keeps_public_fields(self):
        text = repr(
            GcsConfig(
                base64_encoded_private_key_data="c2VjcmV0LWtleQ==",
                project_id="my-project",
                bucket="my-bucket",
            )
        )
        assert "c2VjcmV0LWtleQ==" not in text
        assert "my-project" in text
        assert "my-bucket" in text


class TestObjectMetadata:
    def test_metadata_is_frozen_assignment_raises(self):
        meta = ObjectMetadata(key="k", last_modified=datetime.min, etag="e", size=1)
        try:
            meta.size = 2  # ty: ignore[invalid-assignment]
        except dataclasses.FrozenInstanceError:
            return
        raise AssertionError("expected FrozenInstanceError")

    def test_metadata_optional_fields_default_to_none(self):
        meta = ObjectMetadata(key="k", last_modified=datetime.min, etag="e", size=1)
        assert meta.storage_class is None
        assert meta.owner is None
