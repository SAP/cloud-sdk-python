import pytest

from sap_cloud_sdk.core.dpi_ng.consent.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ClientCreationError,
    ConflictError,
    ConsentSDKError,
    NotFoundError,
    ODataError,
    ValidationError,
)


class TestHierarchy:
    def test_client_creation_error_is_sdk_error(self):
        assert issubclass(ClientCreationError, ConsentSDKError)

    def test_authentication_error_is_sdk_error(self):
        assert issubclass(AuthenticationError, ConsentSDKError)

    def test_authorization_error_is_sdk_error(self):
        assert issubclass(AuthorizationError, ConsentSDKError)

    def test_validation_error_is_sdk_error(self):
        assert issubclass(ValidationError, ConsentSDKError)

    def test_not_found_error_is_sdk_error(self):
        assert issubclass(NotFoundError, ConsentSDKError)

    def test_conflict_error_is_sdk_error(self):
        assert issubclass(ConflictError, ConsentSDKError)

    def test_odata_error_is_sdk_error(self):
        assert issubclass(ODataError, ConsentSDKError)

    def test_all_subclasses_are_exceptions(self):
        for cls in (
            ConsentSDKError,
            ClientCreationError,
            AuthenticationError,
            AuthorizationError,
            ValidationError,
            NotFoundError,
            ConflictError,
            ODataError,
        ):
            assert issubclass(cls, Exception)


class TestConsentSDKError:
    def test_message_stored(self):
        exc = ConsentSDKError("something went wrong")
        assert str(exc) == "something went wrong"

    def test_odata_error_stored_when_provided(self):
        payload = {"code": "DPI-001", "message": "bad input"}
        exc = ConsentSDKError("fail", odata_error=payload)
        assert exc.odata_error == payload

    def test_odata_error_defaults_to_empty_dict(self):
        exc = ConsentSDKError("fail")
        assert exc.odata_error == {}

    def test_odata_error_none_becomes_empty_dict(self):
        exc = ConsentSDKError("fail", odata_error=None)
        assert exc.odata_error == {}

    def test_raise_and_catch(self):
        with pytest.raises(ConsentSDKError, match="something went wrong"):
            raise ConsentSDKError("something went wrong")

    def test_subclass_caught_as_sdk_error(self):
        with pytest.raises(ConsentSDKError):
            raise AuthenticationError("token rejected")


class TestODataError:
    def test_status_code_stored(self):
        exc = ODataError("server error", status_code=500)
        assert exc.status_code == 500

    def test_message_and_status_code(self):
        exc = ODataError("not found", status_code=404)
        assert str(exc) == "not found"
        assert exc.status_code == 404

    def test_odata_error_payload_stored(self):
        payload = {"code": "DPI-404", "message": "resource not found"}
        exc = ODataError("not found", status_code=404, odata_error=payload)
        assert exc.odata_error == payload

    def test_odata_error_defaults_to_empty_dict(self):
        exc = ODataError("error", status_code=500)
        assert exc.odata_error == {}

    def test_raise_and_catch_as_odata_error(self):
        with pytest.raises(ODataError, match="server error"):
            raise ODataError("server error", status_code=500)

    def test_raise_and_catch_as_sdk_error(self):
        with pytest.raises(ConsentSDKError):
            raise ODataError("server error", status_code=500)

    def test_various_status_codes_stored(self):
        for code in (400, 401, 403, 404, 409, 422, 500, 503):
            exc = ODataError("err", status_code=code)
            assert exc.status_code == code
