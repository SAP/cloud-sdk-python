"""Tests for create_client factory function."""

from unittest.mock import MagicMock, Mock, patch
import pytest

from sap_cloud_sdk.objectstore import create_client
from sap_cloud_sdk.objectstore._models import ObjectStoreBindingData


def _make_factory(creds: ObjectStoreBindingData) -> Mock:
    """Return a mock config factory that yields *creds* and has ``has_changed()``."""
    factory = Mock(return_value=creds)
    factory.has_changed = Mock(return_value=False)
    return factory


class TestCreateClient:

    @patch("sap_cloud_sdk.core.secret_resolver.ConfigFactory")
    @patch("sap_cloud_sdk.objectstore.ObjectStoreClient")
    def test_create_client_cloud_mode(self, mock_client_class, mock_factory_class):
        mock_creds = ObjectStoreBindingData(
            access_key_id="k", secret_access_key="s", bucket="b", host="h"
        )
        mock_factory = _make_factory(mock_creds)
        mock_factory_class.return_value = mock_factory

        mock_client = Mock()
        mock_client_class.return_value = mock_client

        result = create_client("production", disable_ssl=True)

        mock_factory_class.assert_called_once_with(
            module="objectstore",
            instance="production",
            binding_cls=ObjectStoreBindingData,
            extract=mock_factory_class.call_args.kwargs["extract"],
        )
        mock_client_class.assert_called_once_with(mock_factory, disable_ssl=True)
        assert result == mock_client

    def test_create_client_empty_instance_raises_error(self):
        with pytest.raises(ValueError, match="instance parameter must be a non-empty string"):
            create_client("")

        with pytest.raises(ValueError, match="instance parameter must be a non-empty string"):
            create_client("   ")

        with pytest.raises(ValueError, match="instance parameter must be a non-empty string"):
            create_client(None)  # type: ignore

    @patch("sap_cloud_sdk.objectstore.ObjectStoreClient")
    def test_create_client_with_explicit_config(self, mock_client_class):
        mock_config = ObjectStoreBindingData(
            access_key_id="explicit_key",
            secret_access_key="explicit_secret",
            bucket="explicit-bucket",
            host="explicit.host.com",
        )
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        result = create_client("ignored-instance", config=mock_config, disable_ssl=True)

        # ObjectStoreClient receives a static factory wrapping the explicit config
        mock_client_class.assert_called_once()
        call_args = mock_client_class.call_args
        factory = call_args.args[0]
        assert call_args.kwargs["disable_ssl"] is True
        assert factory() is mock_config
        assert result == mock_client

    @patch("sap_cloud_sdk.objectstore.ObjectStoreClient")
    def test_create_client_explicit_config_no_has_changed(self, mock_client_class):
        """Static factory for explicit config should not have has_changed (no rotation tracking)."""
        mock_config = ObjectStoreBindingData(
            access_key_id="k", secret_access_key="s", bucket="b", host="h"
        )
        mock_client_class.return_value = Mock()

        create_client("instance", config=mock_config)

        factory = mock_client_class.call_args.args[0]
        assert not hasattr(factory, "has_changed")
