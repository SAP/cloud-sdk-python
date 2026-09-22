"""Deprecation warning for the legacy ``sap_cloud_sdk.objectstore`` package."""

from unittest.mock import Mock, patch

import pytest

from sap_cloud_sdk.objectstore._models import ObjectStoreBindingData
from sap_cloud_sdk.objectstore._s3 import ObjectStoreClient


def _make_factory() -> Mock:
    creds = ObjectStoreBindingData(
        access_key_id="ak",
        secret_access_key="sk",
        bucket="bucket",
        host="s3.amazonaws.com",
    )
    factory = Mock(return_value=creds)
    factory.has_changed = Mock(return_value=False)
    return factory


class TestLegacyDeprecation:
    @patch("sap_cloud_sdk.objectstore._s3.Minio")
    def test_constructing_legacy_client_warns_pointing_to_new_package(self, _minio):
        with pytest.warns(DeprecationWarning, match="object_storage"):
            ObjectStoreClient(_make_factory())
