"""Tests for exception classes."""

import pytest

from sap_cloud_sdk.core.auditlog.exceptions import (
    AuditLogError,
    ClientCreationError,
    TransportError,
    AuthenticationError
)


class TestExceptions:

    def test_exception_hierarchy(self):
        assert issubclass(ClientCreationError, AuditLogError)
        assert issubclass(TransportError, AuditLogError)
        assert issubclass(AuthenticationError, AuditLogError)
        assert issubclass(AuditLogError, Exception)

    def test_base_auditlog_error(self):
        error = AuditLogError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_client_creation_error(self):
        error = ClientCreationError("Failed to create client")
        assert str(error) == "Failed to create client"
        assert isinstance(error, AuditLogError)


    def test_transport_error(self):
        error = TransportError("Transport failed")
        assert str(error) == "Transport failed"
        assert isinstance(error, AuditLogError)


    def test_authentication_error(self):
        error = AuthenticationError("Auth failed")
        assert str(error) == "Auth failed"
        assert isinstance(error, AuditLogError)

    def test_exceptions_with_chained_causes(self):
        original_error = ValueError("Original cause")

        try:
            raise ClientCreationError("Client failed") from original_error
        except ClientCreationError as e:
            assert e.__cause__ is original_error
            assert "Client failed" in str(e)

    def test_exceptions_inherit_standard_behavior(self):
        error_with_args = TransportError("arg1", "arg2")
        assert error_with_args.args == ("arg1", "arg2")

        # Test empty constructor
        empty_error = TransportError()
        assert str(empty_error) == ""
