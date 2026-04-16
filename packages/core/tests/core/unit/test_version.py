"""Tests for version utility."""

import pytest
from unittest.mock import patch, MagicMock
from importlib.metadata import PackageNotFoundError

from sap_cloud_sdk._version import get_version


class TestGetVersion:
    """Test suite for get_version function."""

    @patch('sap_cloud_sdk._version.version')
    def test_get_version_success(self, mock_version):
        """Test that get_version returns the correct version when package is found."""
        expected_version = "1.2.3"
        mock_version.return_value = expected_version

        result = get_version()

        assert result == expected_version
        mock_version.assert_called_once_with("sap-cloud-sdk")

    @patch('sap_cloud_sdk._version.version')
    def test_get_version_package_not_found(self, mock_version):
        """Test that get_version returns 'unknown' when package is not found."""
        mock_version.side_effect = PackageNotFoundError()

        result = get_version()

        assert result == "unknown"
        mock_version.assert_called_once_with("sap-cloud-sdk")

    @patch('sap_cloud_sdk._version.version')
    def test_get_version_generic_exception(self, mock_version):
        """Test that get_version returns 'unknown' on any other exception."""
        mock_version.side_effect = Exception("Some other error")

        result = get_version()

        assert result == "unknown"
        mock_version.assert_called_once_with("sap-cloud-sdk")

    @patch('sap_cloud_sdk._version.version')
    def test_get_version_runtime_error(self, mock_version):
        """Test that get_version returns 'unknown' on RuntimeError."""
        mock_version.side_effect = RuntimeError("Runtime error occurred")

        result = get_version()

        assert result == "unknown"
        mock_version.assert_called_once_with("sap-cloud-sdk")

    @patch('sap_cloud_sdk._version.version')
    def test_get_version_various_version_formats(self, mock_version):
        """Test that get_version works with various version string formats."""
        test_versions = [
            "1.0.0",
            "2.1.3",
            "1.0.0-alpha.1",
            "1.0.0-beta.2",
            "1.0.0-rc.1",
            "1.0.0.dev1",
            "1.0.0+local.build",
        ]

        for version_str in test_versions:
            mock_version.return_value = version_str

            result = get_version()

            assert result == version_str

        # Verify the mock was called the expected number of times
        assert mock_version.call_count == len(test_versions)

    def test_get_version_return_type(self):
        """Test that get_version always returns a string."""
        with patch('sap_cloud_sdk._version.version') as mock_version:
            # Test successful case
            mock_version.return_value = "1.0.0"
            result = get_version()
            assert isinstance(result, str)

            # Test exception case
            mock_version.side_effect = PackageNotFoundError()
            result = get_version()
            assert isinstance(result, str)
