"""Tests for extensibility exception hierarchy."""

import pytest

from sap_cloud_sdk.extensibility.exceptions import (
    ClientCreationError,
    ExtensibilityError,
    TransportError,
)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy and inheritance."""

    def test_extensibility_error_is_exception(self):
        assert issubclass(ExtensibilityError, Exception)

    def test_transport_error_is_extensibility_error(self):
        assert issubclass(TransportError, ExtensibilityError)

    def test_client_creation_error_is_extensibility_error(self):
        assert issubclass(ClientCreationError, ExtensibilityError)

    def test_client_creation_error_caught_by_base(self):
        with pytest.raises(ExtensibilityError):
            raise ClientCreationError("failed")

    def test_transport_error_caught_by_base(self):
        with pytest.raises(ExtensibilityError):
            raise TransportError("transport failure")

    def test_transport_error_message(self):
        err = TransportError("connection refused")
        assert str(err) == "connection refused"

    def test_extensibility_error_message(self):
        err = ExtensibilityError("generic error")
        assert str(err) == "generic error"
