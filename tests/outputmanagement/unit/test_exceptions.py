# SPDX-FileCopyrightText: 2024 SAP SE or an SAP affiliate company
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for output management exceptions."""

import pytest

from sap_cloud_sdk.outputmanagement.exceptions import (
    OutputManagementException,
    ValidationException,
    AuthenticationException,
    NetworkException,
    DestinationNotFoundException,
    DestinationAccessException,
)


class TestOutputManagementExceptions:
    """Test output management exception classes."""

    def test_output_management_exception_basic(self):
        """Test basic OutputManagementException."""
        error = OutputManagementException("Test error")
        assert error.message == "Test error"
        assert isinstance(error, Exception)

    def test_output_management_exception_with_message(self):
        """Test OutputManagementException with custom message."""
        message = "Something went wrong in output management"
        error = OutputManagementException(message)
        assert error.message == message

    def test_output_management_exception_with_error_code(self):
        """Test OutputManagementException with error code."""
        error = OutputManagementException("Test error", error_code="ERR001")
        assert error.message == "Test error"
        assert error.error_code == "ERR001"
        assert "ERR001" in str(error)

    def test_output_management_exception_with_status_code(self):
        """Test OutputManagementException with status code."""
        error = OutputManagementException("Test error", status_code=400)
        assert error.message == "Test error"
        assert error.status_code == 400
        assert "400" in str(error)

    def test_validation_exception(self):
        """Test ValidationException."""
        error = ValidationException("Validation failed")
        assert error.message == "Validation failed"
        assert isinstance(error, OutputManagementException)
        assert isinstance(error, Exception)

    def test_authentication_exception(self):
        """Test AuthenticationException."""
        error = AuthenticationException("Authentication failed")
        assert error.message == "Authentication failed"
        assert isinstance(error, OutputManagementException)
        assert isinstance(error, Exception)

    def test_network_exception(self):
        """Test NetworkException."""
        error = NetworkException("Network error occurred")
        assert error.message == "Network error occurred"
        assert isinstance(error, OutputManagementException)
        assert isinstance(error, Exception)

    def test_destination_not_found_exception(self):
        """Test DestinationNotFoundException."""
        error = DestinationNotFoundException("Destination not found")
        assert error.message == "Destination not found"
        assert isinstance(error, OutputManagementException)

    def test_destination_access_exception(self):
        """Test DestinationAccessException."""
        error = DestinationAccessException("Cannot access destination")
        assert error.message == "Cannot access destination"
        assert isinstance(error, OutputManagementException)

    def test_exception_inheritance_chain(self):
        """Test exception inheritance chain."""
        assert issubclass(ValidationException, OutputManagementException)
        assert issubclass(AuthenticationException, OutputManagementException)
        assert issubclass(NetworkException, OutputManagementException)
        assert issubclass(DestinationNotFoundException, OutputManagementException)
        assert issubclass(DestinationAccessException, OutputManagementException)
        assert issubclass(OutputManagementException, Exception)

    def test_exceptions_can_be_raised(self):
        """Test that exceptions can be raised and caught."""
        with pytest.raises(OutputManagementException):
            raise OutputManagementException("Test")

        with pytest.raises(ValidationException):
            raise ValidationException("Test")

        with pytest.raises(AuthenticationException):
            raise AuthenticationException("Test")

    def test_validation_error_caught_as_base_error(self):
        """Test that ValidationException can be caught as base OutputManagementException."""
        with pytest.raises(OutputManagementException):
            raise ValidationException("Validation failed")

    def test_authentication_error_caught_as_base_error(self):
        """Test that AuthenticationException can be caught as base OutputManagementException."""
        with pytest.raises(OutputManagementException):
            raise AuthenticationException("Auth failed")

    def test_exception_with_empty_message(self):
        """Test exceptions with empty message."""
        error = OutputManagementException("")
        assert error.message == ""

    def test_exception_with_details(self):
        """Test exceptions with additional details."""
        details = {"field": "email", "reason": "invalid format"}
        error = OutputManagementException("Validation error", details=details)
        assert error.details == details
        assert error.details["field"] == "email"
