"""Unit tests for ODataHttpTransport."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata.exceptions import (
    ODataAuthError,
    ODataNotFoundError,
    ODataRequestError,
)


def _mock_response(status_code: int = 200, json_data: Any = None, headers: dict | None = None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.content = b'{"value": []}' if json_data is None else b"data"
    resp.json.return_value = json_data if json_data is not None else {}
    resp.headers = headers or {}
    return resp


@pytest.fixture
def session():
    return MagicMock(spec=requests.Session)


@pytest.fixture
def transport(session):
    return ODataHttpTransport(
        base_url="https://example.com/odata/v4/",
        session=session,
        csrf_enabled=False,
    )


class TestODataHttpTransportGet:
    def test_get_builds_correct_url(self, transport, session):
        session.request.return_value = _mock_response(200, {})
        transport.get("EntitySet")
        call = session.request.call_args
        assert call[1]["url"] == "https://example.com/odata/v4/EntitySet"

    def test_get_passes_params(self, transport, session):
        session.request.return_value = _mock_response(200, {})
        transport.get("EntitySet", params={"$top": "5"})
        call = session.request.call_args
        assert call[1]["params"] == {"$top": "5"}

    def test_get_sets_accept_header(self, transport, session):
        session.request.return_value = _mock_response(200, {})
        transport.get("EntitySet")
        headers = session.request.call_args[1]["headers"]
        assert headers["Accept"] == "application/json"

    def test_get_returns_parsed_json(self, transport, session):
        session.request.return_value = _mock_response(200, {"value": [{"ID": "1"}]})
        data = transport.get("EntitySet")
        assert data == {"value": [{"ID": "1"}]}

    def test_get_404_raises_not_found(self, transport, session):
        session.request.return_value = _mock_response(404)
        with pytest.raises(ODataNotFoundError):
            transport.get("EntitySet")

    def test_get_401_raises_auth_error(self, transport, session):
        session.request.return_value = _mock_response(401)
        with pytest.raises(ODataAuthError):
            transport.get("EntitySet")

    def test_get_500_raises_request_error(self, transport, session):
        session.request.return_value = _mock_response(500)
        with pytest.raises(ODataRequestError):
            transport.get("EntitySet")

    def test_get_204_returns_empty_dict(self, transport, session):
        resp = _mock_response(204)
        resp.content = b""
        session.request.return_value = resp
        assert transport.get("EntitySet") == {}


class TestODataHttpTransportCsrf:
    def test_csrf_fetched_on_post(self, session):
        # CSRF fetch returns the token in a response header
        csrf_resp = MagicMock(spec=requests.Response)
        csrf_resp.status_code = 200
        csrf_resp.headers = {"X-CSRF-Token": "csrf-tok"}

        post_resp = _mock_response(201, {"ID": "1"})
        session.get.return_value = csrf_resp
        session.request.return_value = post_resp

        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=True,
        )
        transport.post("EntitySet", {"Name": "X"})

        headers = session.request.call_args[1]["headers"]
        assert headers["X-CSRF-Token"] == "csrf-tok"

    def test_csrf_retry_on_403(self, session):
        csrf_resp = MagicMock(spec=requests.Response)
        csrf_resp.status_code = 200
        csrf_resp.headers = {"X-CSRF-Token": "tok1"}

        csrf_resp2 = MagicMock(spec=requests.Response)
        csrf_resp2.status_code = 200
        csrf_resp2.headers = {"X-CSRF-Token": "tok2"}

        forbidden = _mock_response(403)
        success = _mock_response(201, {"ID": "1"})

        session.get.side_effect = [csrf_resp, csrf_resp2]
        session.request.side_effect = [forbidden, success]

        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=True,
        )
        transport.post("EntitySet", {"Name": "X"})

        assert session.request.call_count == 2


class TestAbsoluteUrl:
    def test_builds_url_with_trailing_slash(self):
        session = MagicMock(spec=requests.Session)
        t = ODataHttpTransport("https://host/svc/", session, csrf_enabled=False)
        assert t.absolute_url("EntitySet") == "https://host/svc/EntitySet"

    def test_strips_leading_slash_from_path(self):
        session = MagicMock(spec=requests.Session)
        t = ODataHttpTransport("https://host/svc", session, csrf_enabled=False)
        assert t.absolute_url("/EntitySet") == "https://host/svc/EntitySet"
