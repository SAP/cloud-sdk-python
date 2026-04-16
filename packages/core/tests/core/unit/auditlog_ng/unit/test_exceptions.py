"""Tests for exception classes."""

import pytest

from sap_cloud_sdk.auditlog_ng.exceptions import (
    AuditLogNGError,
    ClientCreationError,
    ValidationError
)


class TestExceptions:

    def test_exception_hierarchy(self):
        assert issubclass(ClientCreationError, AuditLogNGError)
        assert issubclass(ValidationError, AuditLogNGError)
        assert issubclass(AuditLogNGError, Exception)

    def test_base_auditlog_ng_error(self):
        error = AuditLogNGError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_client_creation_error(self):
        error = ClientCreationError("Failed to create client")
        assert str(error) == "Failed to create client"
        assert isinstance(error, AuditLogNGError)

    def test_validation_error(self):
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, AuditLogNGError)

    def test_exceptions_with_chained_causes(self):
        original_error = ValueError("Original cause")

        try:
            raise ClientCreationError("Client failed") from original_error
        except ClientCreationError as e:
            assert e.__cause__ is original_error
            assert "Client failed" in str(e)
