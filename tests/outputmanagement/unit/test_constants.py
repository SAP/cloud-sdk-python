# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for output management constants."""

import pytest

from sap_cloud_sdk.outputmanagement.constants import (
    DEFAULT_DESTINATION_NAME,
    OUTPUT_MANAGEMENT_SERVICE_PATH,
    EMAIL_SERVICE_PATH,
)


class TestConstants:
    """Test output management constants."""

    def test_default_destination_name_exists(self):
        """Test default destination name constant exists."""
        assert DEFAULT_DESTINATION_NAME is not None
        assert isinstance(DEFAULT_DESTINATION_NAME, str)
        assert len(DEFAULT_DESTINATION_NAME) > 0

    def test_output_management_service_path_exists(self):
        """Test output management service path constant exists."""
        assert OUTPUT_MANAGEMENT_SERVICE_PATH is not None
        assert isinstance(OUTPUT_MANAGEMENT_SERVICE_PATH, str)
        assert len(OUTPUT_MANAGEMENT_SERVICE_PATH) > 0

    def test_email_service_path_exists(self):
        """Test email service path constant exists."""
        assert EMAIL_SERVICE_PATH is not None
        assert isinstance(EMAIL_SERVICE_PATH, str)
        assert len(EMAIL_SERVICE_PATH) > 0

    def test_service_paths_start_with_slash(self):
        """Test that service paths start with a slash."""
        assert OUTPUT_MANAGEMENT_SERVICE_PATH.startswith("/")
        assert EMAIL_SERVICE_PATH.startswith("/")

    def test_constants_are_strings(self):
        """Test that all constants are strings."""
        assert isinstance(DEFAULT_DESTINATION_NAME, str)
        assert isinstance(OUTPUT_MANAGEMENT_SERVICE_PATH, str)
        assert isinstance(EMAIL_SERVICE_PATH, str)

    def test_constants_not_empty(self):
        """Test that constants are not empty strings."""
        assert DEFAULT_DESTINATION_NAME != ""
        assert OUTPUT_MANAGEMENT_SERVICE_PATH != ""
        assert EMAIL_SERVICE_PATH != ""

    def test_service_paths_format(self):
        """Test service paths follow expected format."""
        # Service paths should be valid URL paths
        assert not OUTPUT_MANAGEMENT_SERVICE_PATH.endswith("/")
        assert not EMAIL_SERVICE_PATH.endswith("/")
        assert " " not in OUTPUT_MANAGEMENT_SERVICE_PATH
        assert " " not in EMAIL_SERVICE_PATH