"""Unit tests for data anonymization SDK exceptions."""

from sap_cloud_sdk.core.data_anonymization.exceptions import (
    AuthenticationError,
    ClientCreationError,
    DataAnonymizationError,
    TransportError,
)


class TestExceptions:
    def test_exception_hierarchy(self) -> None:
        assert issubclass(ClientCreationError, DataAnonymizationError)
        assert issubclass(TransportError, DataAnonymizationError)
        assert issubclass(AuthenticationError, DataAnonymizationError)
        assert issubclass(DataAnonymizationError, Exception)

    def test_exception_messages(self) -> None:
        assert str(DataAnonymizationError("base")) == "base"
        assert str(ClientCreationError("client")) == "client"
        assert str(TransportError("transport")) == "transport"
        assert str(AuthenticationError("auth")) == "auth"

    def test_exception_chaining(self) -> None:
        original_error = ValueError("boom")

        try:
            raise ClientCreationError("failed") from original_error
        except ClientCreationError as error:
            assert error.__cause__ is original_error
