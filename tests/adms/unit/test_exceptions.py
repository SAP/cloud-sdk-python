"""Unit tests for ADMS exception hierarchy."""

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
from sap_cloud_sdk.core.odata.exceptions import ODataNotFoundError, ODataRequestError


class TestExceptionHierarchy:
    def test_adms_errors_are_base(self):
        assert issubclass(ConfigError, AdmsError)
        assert issubclass(AuthError, AdmsError)
        assert issubclass(ClientCreationError, AdmsError)
        assert issubclass(AdmsOperationError, AdmsError)

    def test_operation_errors_are_adms_operation_error(self):
        assert issubclass(ScanNotCleanError, AdmsOperationError)

    def test_document_not_found_is_odata_not_found(self):
        assert DocumentNotFoundError is ODataNotFoundError

    def test_http_error_is_odata_request_error(self):
        assert HttpError is ODataRequestError

    def test_http_error_stores_status_code(self):
        # ODataRequestError takes a response object with status_code and json()
        from unittest.mock import MagicMock

        resp = MagicMock()
        resp.status_code = 400
        resp.json.return_value = {}
        err = HttpError(resp)
        assert err.status_code == 400

    def test_adms_error_is_exception(self):
        with pytest.raises(AdmsError):
            raise AdmsError("base")

    def test_scan_not_clean_is_raised(self):
        with pytest.raises(ScanNotCleanError):
            raise ScanNotCleanError("scan pending")
