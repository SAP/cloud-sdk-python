"""Tests for exception classes."""

import pytest

from sap_cloud_sdk.objectstore.exceptions import (
    ObjectStoreError,
    ClientCreationError,
    ObjectOperationError,
    ObjectNotFoundError,
    ListObjectsError
)


class TestExceptions:

    def test_exception_hierarchy(self):
        assert issubclass(ClientCreationError, ObjectStoreError)
        assert issubclass(ObjectOperationError, ObjectStoreError)
        assert issubclass(ObjectNotFoundError, ObjectOperationError)
        assert issubclass(ListObjectsError, ObjectOperationError)
        assert issubclass(ObjectStoreError, Exception)

    def test_base_objectstore_error(self):
        error = ObjectStoreError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_client_creation_error(self):
        error = ClientCreationError("Failed to create client")
        assert str(error) == "Failed to create client"
        assert isinstance(error, ObjectStoreError)

    def test_object_operation_error(self):
        error = ObjectOperationError("Operation failed")
        assert str(error) == "Operation failed"
        assert isinstance(error, ObjectStoreError)

    def test_object_not_found_error(self):
        error = ObjectNotFoundError("Object not found")
        assert str(error) == "Object not found"
        assert isinstance(error, ObjectOperationError)
        assert isinstance(error, ObjectStoreError)

    def test_list_objects_error(self):
        error = ListObjectsError("List failed")
        assert str(error) == "List failed"
        assert isinstance(error, ObjectOperationError)
        assert isinstance(error, ObjectStoreError)

    def test_exceptions_with_chained_causes(self):
        original_error = ValueError("Original cause")

        try:
            raise ClientCreationError("Client failed") from original_error
        except ClientCreationError as e:
            assert e.__cause__ is original_error
            assert "Client failed" in str(e)

    def test_exceptions_inherit_standard_behavior(self):
        error = ObjectNotFoundError()
        assert str(error) == ""

        error_with_args = ObjectOperationError("arg1", "arg2")
        assert error_with_args.args == ("arg1", "arg2")
