"""Unit tests for binding data and config loading (``object_storage.config``)."""

from unittest.mock import patch

import pytest

from sap_cloud_sdk.object_storage._models import ObjectStoreProvider
from sap_cloud_sdk.object_storage.config import (
    AzureBindingData,
    AzureConfig,
    GcsBindingData,
    GcsConfig,
    S3BindingData,
    S3Config,
    load_from_env_or_mount,
)
from sap_cloud_sdk.object_storage.exceptions import ConfigError

RESOLVER = "sap_cloud_sdk.object_storage.config.read_from_mount_and_fallback_to_env_var"


def _fill(**values):
    """Return a resolver side_effect that populates the ``target`` binding."""

    def side_effect(*, target, **_kwargs):
        for name, value in values.items():
            setattr(target, name, value)

    return side_effect


class TestResolverContract:
    def test_resolver_called_with_objectstore_module_and_instance(self):
        with patch(RESOLVER, side_effect=_fill(**_S3_FULL)) as resolver:
            load_from_env_or_mount(ObjectStoreProvider.S3, "obj-1")
        resolver.assert_called_once()
        kwargs = resolver.call_args.kwargs
        assert kwargs["base_volume_mount"] == "/etc/secrets/appfnd"
        assert kwargs["base_var_name"] == "CLOUD_SDK_CFG"
        assert kwargs["module"] == "objectstore"
        assert kwargs["instance"] == "obj-1"
        assert isinstance(kwargs["target"], S3BindingData)


_S3_FULL = dict(
    access_key_id="ak", secret_access_key="sk", bucket="b", host="h"
)
_AZURE_FULL = dict(container_name="c", container_uri="u", sas_token="t")
_GCS_FULL = dict(base64EncodedPrivateKeyData="k", projectId="p", bucket="b")


class TestLoadSuccess:
    def test_s3_binding_maps_to_s3config_ssl_enabled_by_default(self):
        with patch(RESOLVER, side_effect=_fill(**_S3_FULL)):
            cfg = load_from_env_or_mount(ObjectStoreProvider.S3, "default")
        assert cfg == S3Config(
            access_key_id="ak",
            secret_access_key="sk",
            bucket="b",
            host="h",
            disable_ssl=False,
        )

    def test_azure_binding_maps_to_azureconfig(self):
        with patch(RESOLVER, side_effect=_fill(**_AZURE_FULL)):
            cfg = load_from_env_or_mount(ObjectStoreProvider.AZURE, "default")
        assert cfg == AzureConfig(container_name="c", container_uri="u", sas_token="t")

    def test_gcs_binding_camelcase_maps_to_snake_case_config(self):
        with patch(RESOLVER, side_effect=_fill(**_GCS_FULL)):
            cfg = load_from_env_or_mount(ObjectStoreProvider.GCS, "default")
        assert cfg == GcsConfig(
            base64_encoded_private_key_data="k", project_id="p", bucket="b"
        )


class TestLoadFailure:
    def test_resolver_exception_wrapped_as_config_error(self):
        with patch(RESOLVER, side_effect=RuntimeError("mount blew up")):
            with pytest.raises(ConfigError, match="failed to load") as excinfo:
                load_from_env_or_mount(ObjectStoreProvider.S3, "default")
        assert isinstance(excinfo.value.__cause__, RuntimeError)

    def test_missing_fields_reported_together_s3(self):
        with patch(RESOLVER, side_effect=_fill(access_key_id="ak")):
            with pytest.raises(ConfigError) as excinfo:
                load_from_env_or_mount(ObjectStoreProvider.S3, "default")
        message = str(excinfo.value)
        assert "s3 binding is missing" in message
        for field in ("secret_access_key", "bucket", "host"):
            assert field in message
        assert "access_key_id" not in message


class TestBindingToConfig:
    def test_s3_binding_to_config_honours_disable_ssl(self):
        binding = S3BindingData(
            access_key_id="ak", secret_access_key="sk", bucket="b", host="h"
        )
        assert binding.to_config(disable_ssl=True).disable_ssl is True

    def test_azure_binding_to_config_roundtrips_fields(self):
        binding = AzureBindingData(
            container_name="c", container_uri="u", sas_token="t"
        )
        assert binding.to_config() == AzureConfig(
            container_name="c", container_uri="u", sas_token="t"
        )

    def test_gcs_binding_to_config_roundtrips_fields(self):
        binding = GcsBindingData(
            base64EncodedPrivateKeyData="k", projectId="p", bucket="b"
        )
        assert binding.to_config() == GcsConfig(
            base64_encoded_private_key_data="k", project_id="p", bucket="b"
        )
