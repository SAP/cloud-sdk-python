# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for output management exceptions."""

import pytest

from sap_cloud_sdk.outputmanagement.exceptions import (
    OutputManagementError,
    OutputManagementValidationError,
    OutputManagementClientError,
)


class TestOutputManagementExceptions:
    """Test output management exception classes."""

    def test_output_management_error_basic(self):
        """Test basic OutputManagementError."""
        error = OutputManagementError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_output_management_error_with_message(self):
        """Test OutputManagementError with custom message."""
        message = "Something went wrong in output management"
        error = OutputManagementError(message)
        assert str(error) == message

    def test_output_management_validation_error(self):
        """Test OutputManagementValidationError."""
        error = OutputManagementValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, OutputManagementError)
        assert isinstance(error, Exception)

    def test_output_management_client_error(self):
        """Test OutputManagementClientError."""
        error = OutputManagementClientError("Client error occurred")
        assert str(error) == "Client error occurred"
        assert isinstance(error, OutputManagementError)
        assert isinstance(error, Exception)

    def test_exception_inheritance_chain(self):
        """Test exception inheritance chain."""
        assert issubclass(OutputManagementValidationError, OutputManagementError)
        assert issubclass(OutputManagementClientError, OutputManagementError)
        assert issubclass(OutputManagementError, Exception)

    def test_exceptions_can_be_raised(self):
        """Test that exceptions can be raised and caught."""
        with pytest.raises(OutputManagementError):
            raise OutputManagementError("Test")
        
        with pytest.raises(OutputManagementValidationError):
            raise OutputManagementValidationError("Test")
        
        with pytest.raises(OutputManagementClientError):
            raise OutputManagementClientError("Test")

    def test_validation_error_caught_as_base_error(self):
        """Test that ValidationError can be caught as base OutputManagementError."""
        with pytest.raises(OutputManagementError):
            raise OutputManagementValidationError("Validation failed")

    def test_client_error_caught_as_base_error(self):
        """Test that ClientError can be caught as base OutputManagementError."""
        with pytest.raises(OutputManagementError):
            raise OutputManagementClientError("Client failed")

    def test_exception_with_empty_message(self):
        """Test exceptions with empty message."""
        error = OutputManagementError("")
        assert str(error) == ""

    def test_exception_with_multiline_message(self):
        """Test exceptions with multiline message."""
        message = "Error occurred:\nLine 1\nLine 2"
        error = OutputManagementError(message)
        assert str(error) == message
        assert "\n" in str(error)