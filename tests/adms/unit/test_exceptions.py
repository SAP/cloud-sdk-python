"""Unit tests for DMS exception hierarchy."""

import pytest

from sap_cloud_sdk.adms.exceptions import (
    AuthError,
    ClientCreationError,
    ConfigError,
    AdmsError,
    AdmsOperationError,
    DocumentNotFoundError,
    HttpError,
    ScanNotCleanError,
)


class TestExceptionHierarchy:
    def test_dms_error_is_base(self):
        assert issubclass(ConfigError, AdmsError)
        assert issubclass(HttpError, AdmsError)
        assert issubclass(AuthError, AdmsError)
        assert issubclass(ClientCreationError, AdmsError)
        assert issubclass(AdmsOperationError, AdmsError)

    def test_operation_errors_are_dms_operation_error(self):
        assert issubclass(DocumentNotFoundError, AdmsOperationError)
        assert issubclass(ScanNotCleanError, AdmsOperationError)

    def test_http_error_stores_status_code(self):
        err = HttpError("bad request", status_code=400, response_text="oops")
        assert err.status_code == 400
        assert err.response_text == "oops"
        assert str(err) == "bad request"

    def test_http_error_default_none(self):
        err = HttpError("generic")
        assert err.status_code is None
        assert err.response_text is None

    def test_dms_error_is_exception(self):
        with pytest.raises(AdmsError):
            raise AdmsError("base")

    def test_scan_not_clean_is_raised(self):
        with pytest.raises(ScanNotCleanError):
            raise ScanNotCleanError("scan pending")
