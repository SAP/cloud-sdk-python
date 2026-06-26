"""Unit tests for ODataHttpTransport."""

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from sap_cloud_sdk.core.odata._transport import ODataHttpTransport
from sap_cloud_sdk.core.odata.exceptions import (
    ODataAuthError,
    ODataConnectionError,
    ODataNotFoundError,
    ODataRequestError,
)


def _mock_response(
    status_code: int = 200, json_data: Any = None, headers: dict | None = None
) -> MagicMock:
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


class TestRequest:
    def test_builds_correct_url(self, transport, session):
        session.request.return_value = _mock_response(200, {})
        transport.request("GET", "EntitySet")
        assert (
            session.request.call_args[1]["url"]
            == "https://example.com/odata/v4/EntitySet"
        )

    def test_passes_params(self, transport, session):
        session.request.return_value = _mock_response(200, {})
        transport.request("GET", "EntitySet", params={"$top": "5"})
        assert session.request.call_args[1]["params"] == {"$top": "5"}

    def test_sets_accept_header(self, transport, session):
        session.request.return_value = _mock_response(200, {})
        transport.request("GET", "EntitySet")
        assert session.request.call_args[1]["headers"]["Accept"] == "application/json"

    def test_returns_parsed_json(self, transport, session):
        session.request.return_value = _mock_response(200, {"value": [{"ID": "1"}]})
        assert transport.request("GET", "EntitySet") == {"value": [{"ID": "1"}]}

    def test_404_raises_not_found(self, transport, session):
        session.request.return_value = _mock_response(404)
        with pytest.raises(ODataNotFoundError):
            transport.request("GET", "EntitySet")

    def test_401_raises_auth_error(self, transport, session):
        session.request.return_value = _mock_response(401)
        with pytest.raises(ODataAuthError):
            transport.request("GET", "EntitySet")

    def test_500_raises_request_error(self, transport, session):
        session.request.return_value = _mock_response(500)
        with pytest.raises(ODataRequestError):
            transport.request("GET", "EntitySet")

    def test_204_returns_empty_dict(self, transport, session):
        resp = _mock_response(204)
        resp.content = b""
        session.request.return_value = resp
        assert transport.request("GET", "EntitySet") == {}

    def test_extra_headers_merged(self, transport, session):
        session.request.return_value = _mock_response(200, {})
        transport.request("GET", "EntitySet", headers={"sap-language": "en"})
        assert session.request.call_args[1]["headers"]["sap-language"] == "en"

    def test_passes_method_verbatim(self, transport, session):
        session.request.return_value = _mock_response(201, {"ID": "1"})
        transport.request("POST", "EntitySet", json={"Name": "X"})
        assert session.request.call_args[1]["method"] == "POST"

    def test_connection_error_raises_odata_connection_error(self, transport, session):
        session.request.side_effect = requests.RequestException("timeout")
        with pytest.raises(ODataConnectionError):
            transport.request("GET", "EntitySet")

    def test_403_without_csrf_raises_auth_error(self, session):
        session.request.return_value = _mock_response(403)
        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=False,
        )
        with pytest.raises(ODataAuthError):
            transport.request("GET", "EntitySet")


class TestCsrf:
    def test_csrf_attached_on_post(self, session):
        csrf_resp = MagicMock(spec=requests.Response)
        csrf_resp.status_code = 200
        csrf_resp.headers = {"X-CSRF-Token": "csrf-tok"}
        session.get.return_value = csrf_resp
        session.request.return_value = _mock_response(201, {"ID": "1"})

        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=True,
        )
        transport.request("POST", "EntitySet", json={"Name": "X"})

        assert session.request.call_args[1]["headers"]["X-CSRF-Token"] == "csrf-tok"

    def test_no_csrf_on_get(self, session):
        session.request.return_value = _mock_response(200, {})

        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=True,
        )
        transport.request("GET", "EntitySet")

        assert "X-CSRF-Token" not in session.request.call_args[1]["headers"]
        session.get.assert_not_called()

    def test_csrf_retry_on_403(self, session):
        csrf_resp1 = MagicMock(spec=requests.Response)
        csrf_resp1.status_code = 200
        csrf_resp1.headers = {"X-CSRF-Token": "tok1"}
        csrf_resp2 = MagicMock(spec=requests.Response)
        csrf_resp2.status_code = 200
        csrf_resp2.headers = {"X-CSRF-Token": "tok2"}

        session.get.side_effect = [csrf_resp1, csrf_resp2]
        session.request.side_effect = [
            _mock_response(403),
            _mock_response(201, {"ID": "1"}),
        ]

        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=True,
        )
        transport.request("POST", "EntitySet", json={"Name": "X"})

        assert session.request.call_count == 2

    def test_csrf_retry_uses_fresh_token(self, session):
        csrf_resp1 = MagicMock(spec=requests.Response)
        csrf_resp1.status_code = 200
        csrf_resp1.headers = {"X-CSRF-Token": "tok1"}
        csrf_resp2 = MagicMock(spec=requests.Response)
        csrf_resp2.status_code = 200
        csrf_resp2.headers = {"X-CSRF-Token": "tok2"}

        session.get.side_effect = [csrf_resp1, csrf_resp2]
        session.request.side_effect = [
            _mock_response(403),
            _mock_response(201, {"ID": "1"}),
        ]

        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=True,
        )
        transport.request("POST", "EntitySet", json={"Name": "X"})

        second_call_headers = session.request.call_args_list[1][1]["headers"]
        assert second_call_headers["X-CSRF-Token"] == "tok2"


class TestAbsoluteUrl:
    def test_builds_url_with_trailing_slash(self):
        t = ODataHttpTransport("https://host/svc/", MagicMock(), csrf_enabled=False)
        assert t.absolute_url("EntitySet") == "https://host/svc/EntitySet"

    def test_strips_leading_slash_from_path(self):
        t = ODataHttpTransport("https://host/svc", MagicMock(), csrf_enabled=False)
        assert t.absolute_url("/EntitySet") == "https://host/svc/EntitySet"


class TestGetToken:
    def test_token_injected_as_bearer_header(self, session):
        session.request.return_value = _mock_response(200, {})
        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=False,
            get_token=lambda: "my-token",
        )
        transport.request("GET", "EntitySet")
        headers = session.request.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer my-token"

    def test_token_called_per_request(self, session):
        session.request.return_value = _mock_response(200, {})
        calls = []

        def counter():
            calls.append(1)
            return "t"

        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=False,
            get_token=counter,
        )
        transport.request("GET", "A")
        transport.request("GET", "B")
        assert len(calls) == 2

    def test_token_overrides_session_auth(self, session):
        session.headers = {"Authorization": "Bearer stale"}
        session.request.return_value = _mock_response(200, {})
        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=False,
            get_token=lambda: "fresh",
        )
        transport.request("GET", "EntitySet")
        headers = session.request.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer fresh"

    def test_no_get_token_no_auth_injected(self, session):
        session.request.return_value = _mock_response(200, {})
        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            csrf_enabled=False,
        )
        transport.request("GET", "EntitySet")
        headers = session.request.call_args[1]["headers"]
        assert "Authorization" not in headers

    def test_csrf_fetch_includes_bearer_when_get_token_set(self, session):
        csrf_resp = MagicMock(spec=requests.Response)
        csrf_resp.status_code = 200
        csrf_resp.headers = {"X-CSRF-Token": "csrf-tok"}
        session.get.return_value = csrf_resp
        session.request.return_value = _mock_response(201, {"ID": "1"})
        transport = ODataHttpTransport(
            base_url="https://example.com/odata/v4/",
            session=session,
            get_token=lambda: "bearer-xyz",
            csrf_enabled=True,
        )
        transport.request("POST", "EntitySet", json={})
        csrf_headers = session.get.call_args[1]["headers"]
        assert csrf_headers["Authorization"] == "Bearer bearer-xyz"
