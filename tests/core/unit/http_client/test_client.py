"""Unit tests for HttpClient."""

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests

from sap_cloud_sdk.core.http_client._client import HttpClient
from sap_cloud_sdk.core.http_client.exceptions import (
    HttpConnectionError,
    HttpNotFoundError,
    HttpResponseError,
    HttpUnauthorizedError,
)


def _mock_response(
    status_code: int = 200,
    json_data: Any = None,
    url: str = "https://example.com/api",
) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.url = url
    resp.json.return_value = json_data or {}
    return resp


@pytest.fixture
def session() -> MagicMock:
    return MagicMock(spec=requests.Session)


@pytest.fixture
def client(session: MagicMock) -> HttpClient:
    return HttpClient(
        base_url="https://example.com/api",
        session=session,
    )


class TestRequest:
    def test_builds_correct_url_with_path(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        client.request("GET", "/resources")
        assert session.request.call_args[1]["url"] == "https://example.com/api/resources"

    def test_strips_leading_slash_from_path(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        client.request("GET", "resources")
        assert session.request.call_args[1]["url"] == "https://example.com/api/resources"

    def test_empty_path_uses_base_url(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        client.request("GET")
        assert session.request.call_args[1]["url"] == "https://example.com/api"

    def test_passes_params(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        client.request("GET", "/r", params={"q": "test"})
        assert session.request.call_args[1]["params"] == {"q": "test"}

    def test_passes_json_body(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(201)
        client.request("POST", "/r", json={"name": "x"})
        assert session.request.call_args[1]["json"] == {"name": "x"}

    def test_extra_headers_merged(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        client.request("GET", "/r", headers={"X-Custom": "val"})
        assert session.request.call_args[1]["headers"] == {"X-Custom": "val"}

    def test_method_uppercased(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        client.request("get", "/r")
        assert session.request.call_args[1]["method"] == "GET"

    def test_does_not_raise_on_non_2xx(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(500)
        resp = client.request("GET", "/r")
        assert resp.status_code == 500

    def test_network_error_raises_http_connection_error(
        self, client: HttpClient, session: MagicMock
    ) -> None:
        session.request.side_effect = requests.exceptions.ConnectionError("refused")
        with pytest.raises(HttpConnectionError):
            client.request("GET", "/r")


class TestGet:
    def test_returns_response_on_success(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        resp = client.get("/r")
        assert resp.status_code == 200

    def test_raises_not_found_on_404(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(404)
        with pytest.raises(HttpNotFoundError) as exc_info:
            client.get("/r")
        assert exc_info.value.status_code == 404

    def test_raises_unauthorized_on_401(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(401)
        with pytest.raises(HttpUnauthorizedError) as exc_info:
            client.get("/r")
        assert exc_info.value.status_code == 401

    def test_raises_unauthorized_on_403(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(403)
        with pytest.raises(HttpUnauthorizedError):
            client.get("/r")

    def test_raises_response_error_on_500(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(500)
        with pytest.raises(HttpResponseError) as exc_info:
            client.get("/r")
        assert exc_info.value.status_code == 500

    def test_passes_params(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        client.get("/r", params={"$top": "5"})
        assert session.request.call_args[1]["params"] == {"$top": "5"}


class TestPost:
    def test_sends_post_method(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(201)
        client.post("/r", json={"name": "x"})
        assert session.request.call_args[1]["method"] == "POST"

    def test_raises_on_non_2xx(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(400)
        with pytest.raises(HttpResponseError):
            client.post("/r")


class TestPut:
    def test_sends_put_method(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        client.put("/r/1", json={"name": "updated"})
        assert session.request.call_args[1]["method"] == "PUT"


class TestPatch:
    def test_sends_patch_method(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(200)
        client.patch("/r/1", json={"name": "partial"})
        assert session.request.call_args[1]["method"] == "PATCH"


class TestDelete:
    def test_sends_delete_method(self, client: HttpClient, session: MagicMock) -> None:
        resp = _mock_response(204)
        session.request.return_value = resp
        client.delete("/r/1")
        assert session.request.call_args[1]["method"] == "DELETE"

    def test_raises_not_found_on_404(self, client: HttpClient, session: MagicMock) -> None:
        session.request.return_value = _mock_response(404)
        with pytest.raises(HttpNotFoundError):
            client.delete("/r/1")


class TestBaseUrlNormalisation:
    def test_trailing_slash_stripped_from_base(self, session: MagicMock) -> None:
        client = HttpClient("https://host/api/", session)
        session.request.return_value = _mock_response(200)
        client.request("GET", "resource")
        assert session.request.call_args[1]["url"] == "https://host/api/resource"
