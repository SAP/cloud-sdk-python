"""Tests for objectstore config binding-data and load functions."""

from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.objectstore._models import ObjectStoreProvider
from sap_cloud_sdk.objectstore.config import (
    AzureBindingData,
    AzureConfig,
    GcsBindingData,
    GcsConfig,
    S3BindingData,
    S3Config,
    load_from_env_or_mount,
)
from sap_cloud_sdk.objectstore.exceptions import ConfigError


class TestS3BindingDataValidate:

    def test_validate_raises_when_all_required_fields_empty(self):
        binding = S3BindingData()
        with pytest.raises(ConfigError, match="s3 binding is missing required field"):
            binding.validate()

    def test_validate_raises_and_names_each_missing_field(self):
        binding = S3BindingData(access_key_id="", secret_access_key="", bucket="", host="")
        with pytest.raises(ConfigError) as exc_info:
            binding.validate()
        msg = str(exc_info.value)
        assert "access_key_id" in msg
        assert "secret_access_key" in msg
        assert "bucket" in msg
        assert "host" in msg

    def test_validate_raises_naming_only_the_missing_field(self):
        binding = S3BindingData(
            access_key_id="key", secret_access_key="secret", bucket="", host="host"
        )
        with pytest.raises(ConfigError) as exc_info:
            binding.validate()
        msg = str(exc_info.value)
        assert "bucket" in msg
        assert "access_key_id" not in msg
        assert "secret_access_key" not in msg
        assert "host" not in msg

    def test_validate_does_not_raise_when_all_required_fields_populated(self):
        binding = S3BindingData(
            access_key_id="key",
            secret_access_key="secret",
            bucket="my-bucket",
            host="s3.example.com",
        )
        binding.validate()  # must not raise


class TestS3BindingDataToConfig:

    def test_to_config_maps_fields_onto_s3_config(self):
        binding = S3BindingData(
            access_key_id="key",
            secret_access_key="secret",
            bucket="my-bucket",
            host="s3.example.com",
        )
        cfg = binding.to_config()
        assert isinstance(cfg, S3Config)
        assert cfg.access_key_id == "key"
        assert cfg.secret_access_key == "secret"
        assert cfg.bucket == "my-bucket"
        assert cfg.host == "s3.example.com"

    def test_to_config_defaults_disable_ssl_to_false(self):
        binding = S3BindingData(
            access_key_id="k", secret_access_key="s", bucket="b", host="h"
        )
        cfg = binding.to_config()
        assert cfg.disable_ssl is False

    def test_to_config_sets_disable_ssl_true_when_passed(self):
        binding = S3BindingData(
            access_key_id="k", secret_access_key="s", bucket="b", host="h"
        )
        cfg = binding.to_config(disable_ssl=True)
        assert cfg.disable_ssl is True


class TestAzureBindingDataValidate:

    def test_validate_raises_when_all_required_fields_empty(self):
        binding = AzureBindingData()
        with pytest.raises(ConfigError, match="azure binding is missing required field"):
            binding.validate()

    def test_validate_raises_and_names_each_missing_field(self):
        binding = AzureBindingData(container_uri="", sas_token="")
        with pytest.raises(ConfigError) as exc_info:
            binding.validate()
        msg = str(exc_info.value)
        assert "container_uri" in msg
        assert "sas_token" in msg

    def test_validate_raises_naming_only_the_missing_field(self):
        binding = AzureBindingData(container_uri="https://example.com/c", sas_token="")
        with pytest.raises(ConfigError) as exc_info:
            binding.validate()
        msg = str(exc_info.value)
        assert "sas_token" in msg
        assert "container_uri" not in msg

    def test_validate_does_not_raise_when_required_fields_populated(self):
        binding = AzureBindingData(
            container_uri="https://account.blob.core.windows.net/container",
            sas_token="sv=2020",
        )
        binding.validate()  # must not raise


class TestAzureBindingDataToConfig:

    def test_to_config_maps_fields_onto_azure_config(self):
        binding = AzureBindingData(
            account_name="account",
            container_name="container",
            container_uri="https://account.blob.core.windows.net/container",
            region="westus",
            sas_token="sv=2020",
        )
        cfg = binding.to_config()
        assert isinstance(cfg, AzureConfig)
        assert cfg.account_name == "account"
        assert cfg.container_name == "container"
        assert cfg.container_uri == "https://account.blob.core.windows.net/container"
        assert cfg.region == "westus"
        assert cfg.sas_token == "sv=2020"


class TestGcsBindingDataValidate:

    def test_validate_raises_when_all_required_fields_empty(self):
        binding = GcsBindingData()
        with pytest.raises(ConfigError, match="gcs binding is missing required field"):
            binding.validate()

    def test_validate_raises_and_names_each_missing_field(self):
        binding = GcsBindingData(
            base64EncodedPrivateKeyData="", projectId="", bucket=""
        )
        with pytest.raises(ConfigError) as exc_info:
            binding.validate()
        msg = str(exc_info.value)
        assert "base64EncodedPrivateKeyData" in msg
        assert "projectId" in msg
        assert "bucket" in msg

    def test_validate_raises_naming_only_the_missing_field(self):
        binding = GcsBindingData(
            base64EncodedPrivateKeyData="data", projectId="proj", bucket=""
        )
        with pytest.raises(ConfigError) as exc_info:
            binding.validate()
        msg = str(exc_info.value)
        assert "bucket" in msg
        assert "base64EncodedPrivateKeyData" not in msg
        assert "projectId" not in msg

    def test_validate_does_not_raise_when_all_required_fields_populated(self):
        binding = GcsBindingData(
            base64EncodedPrivateKeyData="dGVzdA==",
            projectId="my-project",
            bucket="my-bucket",
        )
        binding.validate()  # must not raise


class TestGcsBindingDataToConfig:

    def test_to_config_maps_camel_case_to_snake_case(self):
        binding = GcsBindingData(
            base64EncodedPrivateKeyData="dGVzdA==",
            projectId="my-project",
            bucket="my-bucket",
        )
        cfg = binding.to_config()
        assert isinstance(cfg, GcsConfig)
        # camelCase binding attrs map to snake_case config fields
        assert cfg.base64_encoded_private_key_data == "dGVzdA=="
        assert cfg.project_id == "my-project"
        assert cfg.bucket == "my-bucket"


_RESOLVER_PATH = "sap_cloud_sdk.objectstore.config.read_from_mount_and_fallback_to_env_var"


class TestLoadFromEnvOrMountS3:

    def test_returns_s3_config_for_s3_provider(self):
        def populate_binding(
            base_volume_mount, base_var_name, module, instance, target
        ):
            target.access_key_id = "key"
            target.secret_access_key = "secret"
            target.bucket = "bucket"
            target.host = "host"

        with patch(_RESOLVER_PATH, side_effect=populate_binding):
            cfg = load_from_env_or_mount(ObjectStoreProvider.S3, "default")

        assert isinstance(cfg, S3Config)
        assert cfg.access_key_id == "key"

    def test_resolver_called_with_module_objectstore_and_instance(self):
        def populate_binding(*, module, instance, target, **_):
            target.access_key_id = "k"
            target.secret_access_key = "s"
            target.bucket = "b"
            target.host = "h"

        mock_resolver = MagicMock(side_effect=populate_binding)

        with patch(_RESOLVER_PATH, mock_resolver):
            load_from_env_or_mount(ObjectStoreProvider.S3, "my-instance")

        mock_resolver.assert_called_once()
        kwargs = mock_resolver.call_args.kwargs
        assert kwargs["module"] == "objectstore"
        assert kwargs["instance"] == "my-instance"

    def test_resolver_exception_wrapped_in_config_error(self):
        with patch(_RESOLVER_PATH, side_effect=RuntimeError("network error")):
            with pytest.raises(ConfigError, match="my-instance"):
                load_from_env_or_mount(ObjectStoreProvider.S3, "my-instance")

    def test_binding_validation_failure_raises_config_error(self):
        # Resolver succeeds but leaves fields empty → validate() fails.
        with patch(_RESOLVER_PATH):  # no-op: leaves binding with empty strings
            with pytest.raises(ConfigError, match="s3 binding is missing required field"):
                load_from_env_or_mount(ObjectStoreProvider.S3, "default")


class TestLoadFromEnvOrMountAzure:

    def test_returns_azure_config_for_azure_provider(self):
        def populate_binding(
            base_volume_mount, base_var_name, module, instance, target
        ):
            target.container_uri = "https://example.com/c"
            target.sas_token = "sv=2020"

        with patch(_RESOLVER_PATH, side_effect=populate_binding):
            cfg = load_from_env_or_mount(ObjectStoreProvider.AZURE, "default")

        assert isinstance(cfg, AzureConfig)
        assert cfg.sas_token == "sv=2020"

    def test_binding_validation_failure_raises_config_error_for_azure(self):
        with patch(_RESOLVER_PATH):
            with pytest.raises(ConfigError, match="azure binding is missing required field"):
                load_from_env_or_mount(ObjectStoreProvider.AZURE, "default")


class TestLoadFromEnvOrMountGcs:

    def test_returns_gcs_config_for_gcs_provider(self):
        def populate_binding(
            base_volume_mount, base_var_name, module, instance, target
        ):
            target.base64EncodedPrivateKeyData = "dGVzdA=="
            target.projectId = "my-project"
            target.bucket = "my-bucket"

        with patch(_RESOLVER_PATH, side_effect=populate_binding):
            cfg = load_from_env_or_mount(ObjectStoreProvider.GCS, "default")

        assert isinstance(cfg, GcsConfig)
        assert cfg.project_id == "my-project"
        assert cfg.base64_encoded_private_key_data == "dGVzdA=="

    def test_binding_validation_failure_raises_config_error_for_gcs(self):
        with patch(_RESOLVER_PATH):
            with pytest.raises(ConfigError, match="gcs binding is missing required field"):
                load_from_env_or_mount(ObjectStoreProvider.GCS, "default")
