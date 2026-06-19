# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for output management constants."""

import pytest

from sap_cloud_sdk.outputmanagement.constants import (
    Constants,
    FileFormat,
    Channel,
    Status,
)


class TestConstants:
    """Test output management constants."""

    def test_api_output_control_exists(self):
        """Test API output control constant exists."""
        assert Constants.API_OUTPUT_CONTROL is not None
        assert isinstance(Constants.API_OUTPUT_CONTROL, str)
        assert len(Constants.API_OUTPUT_CONTROL) > 0

    def test_api_output_control_starts_with_slash(self):
        """Test that API path starts with a slash."""
        assert Constants.API_OUTPUT_CONTROL.startswith("/")

    def test_header_constants_exist(self):
        """Test that header constants exist."""
        assert Constants.CONTENT_TYPE is not None
        assert Constants.APPLICATION_JSON is not None
        assert Constants.AUTHORIZATION is not None
        assert Constants.BEARER is not None

    def test_header_constants_are_strings(self):
        """Test that header constants are strings."""
        assert isinstance(Constants.CONTENT_TYPE, str)
        assert isinstance(Constants.APPLICATION_JSON, str)
        assert isinstance(Constants.AUTHORIZATION, str)
        assert isinstance(Constants.BEARER, str)

    def test_content_type_constants(self):
        """Test content type constants."""
        assert Constants.CONTENT_TYPE_JSON == "application/json"
        assert Constants.CONTENT_TYPE_PDF == "application/pdf"

    def test_file_format_enum(self):
        """Test FileFormat enum."""
        assert FileFormat.PDF.value == "PDF"
        assert FileFormat.DOCX.value == "DOCX"
        assert FileFormat.HTML.value == "HTML"
        assert FileFormat.XML.value == "XML"

    def test_channel_enum(self):
        """Test Channel enum."""
        assert Channel.EMAIL.value == "EMAIL"
        assert Channel.INTERNAL_EMAIL.value == "INTERNAL_EMAIL"
        assert Channel.DIRECT_SHARE.value == "DIRECT_SHARE"
        assert Channel.FORM.value == "FORM"

    def test_status_enum(self):
        """Test Status enum."""
        assert Status.PENDING.value == "PENDING"
        assert Status.IN_PROGRESS.value == "IN_PROGRESS"
        assert Status.COMPLETED.value == "COMPLETED"
        assert Status.FAILED.value == "FAILED"
        assert Status.CANCELLED.value == "CANCELLED"
