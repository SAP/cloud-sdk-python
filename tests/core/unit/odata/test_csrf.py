"""Unit tests for CsrfTokenProvider."""

from unittest.mock import MagicMock

import pytest
import requests

from sap_cloud_sdk.core.odata._csrf import CsrfTokenProvider
from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata.exceptions import ODataCsrfError


def _make_transport(session: requests.Session) -> ODataHttpTransport:
    return ODataHttpTransport(
        base_url="https://example.com/odata/v4",
        session=session,
        csrf_enabled=False,  # we manage CsrfTokenProvider manually in these tests
    )


class TestCsrfTokenProvider:
    def test_returns_token_from_response_header(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.headers = {"X-CSRF-Token": "my-token"}
        session.get.return_value = resp

        provider = CsrfTokenProvider(_make_transport(session))
        assert provider.get() == "my-token"

    def test_caches_token(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.headers = {"X-CSRF-Token": "cached"}
        session.get.return_value = resp

        provider = CsrfTokenProvider(_make_transport(session))
        provider.get()
        provider.get()
        assert session.get.call_count == 1

    def test_invalidate_clears_cache(self):
        session = MagicMock(spec=requests.Session)
        resp1 = MagicMock(spec=requests.Response)
        resp1.status_code = 200
        resp1.headers = {"X-CSRF-Token": "tok1"}
        resp2 = MagicMock(spec=requests.Response)
        resp2.status_code = 200
        resp2.headers = {"X-CSRF-Token": "tok2"}
        session.get.side_effect = [resp1, resp2]

        provider = CsrfTokenProvider(_make_transport(session))
        assert provider.get() == "tok1"
        provider.invalidate()
        assert provider.get() == "tok2"
        assert session.get.call_count == 2

    def test_raises_csrf_error_when_no_token_in_response(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.headers = {}
        session.get.return_value = resp

        provider = CsrfTokenProvider(_make_transport(session))
        with pytest.raises(ODataCsrfError):
            provider.get()

    def test_raises_csrf_error_on_network_failure(self):
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = requests.RequestException("timeout")

        provider = CsrfTokenProvider(_make_transport(session))
        with pytest.raises(ODataCsrfError, match="CSRF fetch failed"):
            provider.get()
