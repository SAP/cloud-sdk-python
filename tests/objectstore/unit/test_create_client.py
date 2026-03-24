"""Tests for create_client factory function."""

from unittest.mock import Mock, patch
import pytest

from sap_cloud_sdk.objectstore import create_client
from sap_cloud_sdk.objectstore._models import ObjectStoreBindingData


class TestCreateClient:

    @patch('sap_cloud_sdk.objectstore.read_from_mount_and_fallback_to_env_var')
    @patch('sap_cloud_sdk.objectstore.ObjectStoreClient')
    def test_create_client_cloud_mode(self, mock_client_class, mock_resolver):
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        result = create_client("production", disable_ssl=True)

        mock_resolver.assert_called_once()
        call_args = mock_resolver.call_args
        assert call_args[1]["module"] == "objectstore"
        assert call_args[1]["instance"] == "production"
        assert isinstance(call_args[1]["target"], ObjectStoreBindingData)
        mock_client_class.assert_called_once_with(call_args[1]["target"], disable_ssl=True)
        assert result == mock_client

    def test_create_client_empty_instance_raises_error(self):
        """Test that create_client raises ValueError for empty instance."""
        with pytest.raises(ValueError, match="instance parameter must be a non-empty string"):
            create_client("")

        with pytest.raises(ValueError, match="instance parameter must be a non-empty string"):
            create_client("   ")  # whitespace only

        with pytest.raises(ValueError, match="instance parameter must be a non-empty string"):
            create_client(None)  # type: ignore


    @patch('sap_cloud_sdk.objectstore.ObjectStoreClient')
    def test_create_client_with_explicit_config(self, mock_client_class):
        """Test that create_client uses explicit config when provided."""
        mock_config = ObjectStoreBindingData(
            access_key_id="explicit_key",
            secret_access_key="explicit_secret",
            bucket="explicit-bucket",
            host="explicit.host.com"
        )
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        result = create_client("ignored-instance", config=mock_config, disable_ssl=True)

        mock_client_class.assert_called_once_with(mock_config, disable_ssl=True)
        assert result == mock_client
