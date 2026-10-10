"""Unit tests for the object store client factory (``object_storage._factory``)."""

from unittest.mock import patch

import pytest

from sap_cloud_sdk.core.secret_resolver import ConfigFactory
from sap_cloud_sdk.object_storage import create_client
from sap_cloud_sdk.object_storage._models import ObjectStoreProvider
from sap_cloud_sdk.object_storage.config import (
    AzureConfig,
    GcsConfig,
    S3BindingData,
    S3Config,
)
from sap_cloud_sdk.object_storage.exceptions import ClientCreationError

S3_CONFIG = S3Config(access_key_id="ak", secret_access_key="sk", bucket="b", host="h")
AZURE_CONFIG = AzureConfig(container_name="c", container_uri="u", sas_token="t")
GCS_CONFIG = GcsConfig(base64_encoded_private_key_data="k", project_id="p", bucket="b")


def _sole_factory_arg(ctor):
    """Return the single positional factory the client ctor was called with."""
    (factory,), _ = ctor.call_args
    return factory


class TestExplicitConfigRouting:
    def test_s3_config_dispatches_to_s3_client_via_static_factory(self):
        with patch("sap_cloud_sdk.object_storage._factory.S3Client") as ctor:
            assert create_client(config=S3_CONFIG) is ctor.return_value
            factory = _sole_factory_arg(ctor)
            assert factory() is S3_CONFIG
            # Explicit config must not carry rotation tracking.
            assert not hasattr(factory, "has_changed")

    def test_azure_config_dispatches_to_azure_client_via_static_factory(self):
        with patch("sap_cloud_sdk.object_storage._factory.AzureClient") as ctor:
            assert create_client(config=AZURE_CONFIG) is ctor.return_value
            assert _sole_factory_arg(ctor)() is AZURE_CONFIG

    def test_gcs_config_dispatches_to_gcs_client_via_static_factory(self):
        with patch("sap_cloud_sdk.object_storage._factory.GcsClient") as ctor:
            assert create_client(config=GCS_CONFIG) is ctor.return_value
            assert _sole_factory_arg(ctor)() is GCS_CONFIG

    def test_instance_ignored_when_config_provided(self):
        with (
            patch("sap_cloud_sdk.object_storage._factory.S3Client"),
            patch("sap_cloud_sdk.object_storage._factory.read_binding_keys") as read,
        ):
            create_client(instance="anything", config=S3_CONFIG)
            read.assert_not_called()

    def test_unsupported_config_type_raises_client_creation_error(self):
        with pytest.raises(ClientCreationError, match="Unsupported config type"):
            create_client(config=object())  # ty: ignore[invalid-argument-type]


class TestAutoDetectPath:
    def test_default_instance_used_when_none_given(self):
        with (
            patch("sap_cloud_sdk.object_storage._factory.read_binding_keys") as read,
            patch(
                "sap_cloud_sdk.object_storage._factory.detect_provider",
                return_value=ObjectStoreProvider.S3,
            ),
            patch("sap_cloud_sdk.object_storage._factory.S3Client"),
        ):
            create_client()
            read.assert_called_once_with("default")

    def test_auto_detect_builds_config_factory_for_detected_provider(self):
        with (
            patch("sap_cloud_sdk.object_storage._factory.read_binding_keys"),
            patch(
                "sap_cloud_sdk.object_storage._factory.detect_provider",
                return_value=ObjectStoreProvider.S3,
            ),
            patch("sap_cloud_sdk.object_storage._factory.S3Client") as ctor,
        ):
            create_client(instance="obj-1")
            factory = _sole_factory_arg(ctor)
            assert isinstance(factory, ConfigFactory)
            # Rotation tracking is available on the auto-detect path.
            assert callable(factory.has_changed)
            assert factory._module == "objectstore"
            assert factory._instance == "obj-1"
            assert factory._binding_cls is S3BindingData

    def test_detection_valueerror_wrapped_as_client_creation_error(self):
        with (
            patch("sap_cloud_sdk.object_storage._factory.read_binding_keys"),
            patch(
                "sap_cloud_sdk.object_storage._factory.detect_provider",
                side_effect=ValueError("Cannot detect objectstore provider"),
            ),
        ):
            with pytest.raises(ClientCreationError, match="obj-1") as excinfo:
                create_client(instance="obj-1")
        assert isinstance(excinfo.value.__cause__, ValueError)
