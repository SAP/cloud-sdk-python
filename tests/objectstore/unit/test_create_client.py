"""Tests for create_client factory function."""

from unittest.mock import MagicMock, patch
import pytest

from sap_cloud_sdk.objectstore import create_client
from sap_cloud_sdk.objectstore.config import (
    AzureBindingData,
    AzureConfig,
    GcsBindingData,
    GcsConfig,
    S3BindingData,
    S3Config,
)
from sap_cloud_sdk.objectstore.exceptions import ClientCreationError


class TestCreateClientValidation:

    def test_create_client_empty_instance_raises_value_error(self):
        with pytest.raises(ValueError, match="instance parameter must be a non-empty string"):
            create_client("")

    def test_create_client_whitespace_only_instance_raises_value_error(self):
        with pytest.raises(ValueError, match="instance parameter must be a non-empty string"):
            create_client("   ")

    def test_create_client_none_instance_raises_value_error(self):
        with pytest.raises(ValueError, match="instance parameter must be a non-empty string"):
            create_client(None)  # type: ignore


class TestCreateClientExplicitConfig:

    @patch("sap_cloud_sdk.objectstore._factory.S3Client")
    def test_create_client_with_s3_config_returns_s3_client(self, mock_s3_class):
        mock_instance = MagicMock()
        mock_s3_class.return_value = mock_instance
        config = S3Config(
            access_key_id="key",
            secret_access_key="secret",
            bucket="bucket",
            host="s3.example.com",
        )

        result = create_client("any-instance", config=config)

        mock_s3_class.assert_called_once_with(config)
        assert result is mock_instance

    @patch("sap_cloud_sdk.objectstore._factory.AzureClient")
    def test_create_client_with_azure_config_returns_azure_client(self, mock_azure_class):
        mock_instance = MagicMock()
        mock_azure_class.return_value = mock_instance
        config = AzureConfig(
            account_name="account",
            container_name="container",
            container_uri="https://account.blob.core.windows.net/container",
            region="westus",
            sas_token="sv=...",
        )

        result = create_client("any-instance", config=config)

        mock_azure_class.assert_called_once_with(config)
        assert result is mock_instance

    @patch("sap_cloud_sdk.objectstore._factory.GcsClient")
    def test_create_client_with_gcs_config_returns_gcs_client(self, mock_gcs_class):
        mock_instance = MagicMock()
        mock_gcs_class.return_value = mock_instance
        config = GcsConfig(
            base64_encoded_private_key_data="dGVzdA==",
            project_id="my-project",
            bucket="my-bucket",
        )

        result = create_client("any-instance", config=config)

        mock_gcs_class.assert_called_once_with(config)
        assert result is mock_instance

    def test_create_client_with_unknown_config_type_raises_client_creation_error(self):
        with pytest.raises(ClientCreationError, match="Unsupported config type"):
            create_client("any-instance", config=object())  # type: ignore


class TestCreateClientAutoDetection:

    @patch("sap_cloud_sdk.objectstore._factory.S3Client")
    @patch("sap_cloud_sdk.objectstore._factory.load_from_env_or_mount")
    @patch("sap_cloud_sdk.objectstore._factory.read_binding_keys")
    def test_create_client_autodetects_s3(
        self, mock_read_keys, mock_load, mock_s3_class
    ):
        s3_keys = {"access_key_id", "secret_access_key", "host", "bucket"}
        mock_read_keys.return_value = s3_keys
        mock_config = S3Config(
            access_key_id="", secret_access_key="", bucket="", host=""
        )
        mock_load.return_value = mock_config
        mock_instance = MagicMock()
        mock_s3_class.return_value = mock_instance

        result = create_client("default")

        mock_read_keys.assert_called_once_with("default")
        mock_load.assert_called_once_with("s3", "default")
        mock_s3_class.assert_called_once_with(mock_config)
        assert result is mock_instance

    @patch("sap_cloud_sdk.objectstore._factory.AzureClient")
    @patch("sap_cloud_sdk.objectstore._factory.load_from_env_or_mount")
    @patch("sap_cloud_sdk.objectstore._factory.read_binding_keys")
    def test_create_client_autodetects_azure(
        self, mock_read_keys, mock_load, mock_azure_class
    ):
        azure_keys = {"container_uri", "sas_token", "container_name", "account_name"}
        mock_read_keys.return_value = azure_keys
        mock_config = AzureConfig(
            account_name="", container_name="", container_uri="", region="", sas_token=""
        )
        mock_load.return_value = mock_config
        mock_instance = MagicMock()
        mock_azure_class.return_value = mock_instance

        result = create_client("my-azure-instance")

        mock_load.assert_called_once_with("azure", "my-azure-instance")
        mock_azure_class.assert_called_once_with(mock_config)
        assert result is mock_instance

    @patch("sap_cloud_sdk.objectstore._factory.GcsClient")
    @patch("sap_cloud_sdk.objectstore._factory.load_from_env_or_mount")
    @patch("sap_cloud_sdk.objectstore._factory.read_binding_keys")
    def test_create_client_autodetects_gcs(
        self, mock_read_keys, mock_load, mock_gcs_class
    ):
        gcs_keys = {"base64encodedprivatekeydata", "projectid", "bucket", "region"}
        mock_read_keys.return_value = gcs_keys
        mock_config = GcsConfig(
            base64_encoded_private_key_data="", project_id="", bucket=""
        )
        mock_load.return_value = mock_config
        mock_instance = MagicMock()
        mock_gcs_class.return_value = mock_instance

        result = create_client("my-gcs-instance")

        mock_load.assert_called_once_with("gcs", "my-gcs-instance")
        mock_gcs_class.assert_called_once_with(mock_config)
        assert result is mock_instance

    @patch("sap_cloud_sdk.objectstore._factory.read_binding_keys")
    def test_create_client_no_matching_provider_raises_client_creation_error(
        self, mock_read_keys
    ):
        mock_read_keys.return_value = {"garbage", "unknown_key"}

        with pytest.raises(ClientCreationError):
            create_client("unknown-instance")
