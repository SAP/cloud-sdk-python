"""Unit tests for HttpInvoker (get, post, put, delete, post_form, get_stream)."""

from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from sap_cloud_sdk.dms._http import HttpInvoker
from sap_cloud_sdk.core.protocol.http import HttpMethod, XsuaaAuthProvider
from sap_cloud_sdk.dms.exceptions import (
    DMSConflictException,
    DMSConnectionError,
    DMSInvalidArgumentException,
    DMSObjectNotFoundException,
    DMSPermissionDeniedException,
    DMSRuntimeException,
)


def _make_response(status_code=200, json_data=None, text=""):
    resp = Mock()
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


@pytest.fixture
def mock_auth_provider():
    return Mock(spec=XsuaaAuthProvider)


@pytest.fixture
def mock_http_client():
    return Mock()


@pytest.fixture
def invoker(mock_auth_provider, mock_http_client):
    with patch("sap_cloud_sdk.dms._http.HttpClient", return_value=mock_http_client):
        inv = HttpInvoker(
            auth_provider=mock_auth_provider,
            base_url="https://api.example.com",
            connect_timeout=5,
            read_timeout=15,
        )
    return inv, mock_http_client


# ---------------------------------------------------------------
# GET
# ---------------------------------------------------------------


class TestGet:
    def test_get_basic(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(200, {"key": "val"})

        result = inv.get("/rest/v2/repos")

        http.request.assert_called_once()
        call_args = http.request.call_args
        assert call_args[0][0] == HttpMethod.GET
        assert call_args[0][1] == "/rest/v2/repos"
        assert result.status_code == 200

    def test_get_with_params(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(200)

        inv.get("/path", params={"objectId": "abc", "cmisselector": "acl"})

        call_kwargs = http.request.call_args[1]
        assert call_kwargs["params"] == {"objectId": "abc", "cmisselector": "acl"}

    def test_get_with_tenant(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(200)

        inv.get("/path", tenant_subdomain="sub1")

        call_kwargs = http.request.call_args[1]
        assert call_kwargs["tenant_subdomain"] == "sub1"

    def test_get_404_raises_not_found(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(404, text="Not Found")

        with pytest.raises(DMSObjectNotFoundException) as exc_info:
            inv.get("/missing")
        assert exc_info.value.status_code == 404

    def test_get_400_raises_invalid_argument(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(400, text="Bad Request")

        with pytest.raises(DMSInvalidArgumentException) as exc_info:
            inv.get("/bad")
        assert exc_info.value.status_code == 400

    def test_get_401_raises_permission_denied(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(401, text="Unauthorized")

        with pytest.raises(DMSPermissionDeniedException) as exc_info:
            inv.get("/unauthorized")
        assert exc_info.value.status_code == 401

    def test_get_500_raises_runtime(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(500, text="Internal Server Error")

        with pytest.raises(DMSRuntimeException) as exc_info:
            inv.get("/error")
        assert exc_info.value.status_code == 500

    def test_get_connection_error(self, invoker):
        inv, http = invoker
        http.request.side_effect = requests.exceptions.ConnectionError("refused")

        with pytest.raises(DMSConnectionError):
            inv.get("/unreachable")

    def test_get_timeout_error(self, invoker):
        inv, http = invoker
        http.request.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(DMSConnectionError):
            inv.get("/slow")


# ---------------------------------------------------------------
# Error message extraction
# ---------------------------------------------------------------


class TestErrorMessageExtraction:
    def test_400_extracts_json_message(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(
            400,
            json_data={"exception": "versioning", "message": "The object is not the latest version"},
            text='{"message": "The object is not the latest version"}',
        )

        with pytest.raises(DMSInvalidArgumentException) as exc_info:
            inv.get("/bad")
        assert "The object is not the latest version" in str(exc_info.value)

    def test_400_fallback_when_no_json(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(400, text="Bad Request")

        with pytest.raises(DMSInvalidArgumentException) as exc_info:
            inv.get("/bad")
        assert "Request contains invalid or disallowed parameters" in str(exc_info.value)

    def test_404_extracts_json_message(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(
            404,
            json_data={"message": "Document abc-123 not found"},
            text='{"message": "Document abc-123 not found"}',
        )

        with pytest.raises(DMSObjectNotFoundException) as exc_info:
            inv.get("/missing")
        assert "Document abc-123 not found" in str(exc_info.value)

    def test_409_raises_conflict(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(
            409,
            json_data={"message": "Object already exists with name test.txt"},
            text='{"message": "Object already exists with name test.txt"}',
        )

        with pytest.raises(DMSConflictException) as exc_info:
            inv.get("/conflict")
        assert exc_info.value.status_code == 409
        assert "Object already exists with name test.txt" in str(exc_info.value)

    def test_409_fallback_when_no_json(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(409, text="Conflict")

        with pytest.raises(DMSConflictException) as exc_info:
            inv.get("/conflict")
        assert "conflicts with the current state" in str(exc_info.value)


# ---------------------------------------------------------------
# POST (form-encoded)
# ---------------------------------------------------------------


class TestPostForm:
    def test_post_form_basic(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(201, {"succinctProperties": {}})

        form = {"cmisaction": "createFolder", "objectId": "root-id"}
        result = inv.post_form("/browser/repo1/root", data=form)

        http.request.assert_called_once()
        call_args = http.request.call_args
        assert call_args[0][0] == HttpMethod.POST
        assert call_args[0][1] == "/browser/repo1/root"
        call_kwargs = http.request.call_args[1]
        assert call_kwargs["data"] == form
        assert result.status_code == 201

    def test_post_form_no_content_type_header(self, invoker):
        """post_form must NOT set Content-Type — let requests handle it."""
        inv, http = invoker
        http.request.return_value = _make_response(201)

        inv.post_form("/path", data={"key": "val"})

        headers_sent = http.request.call_args[1]["headers"]
        assert "Content-Type" not in headers_sent

    def test_post_form_with_files(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(201)

        files = {"media": ("test.pdf", b"content", "application/pdf")}
        inv.post_form("/path", data={"cmisaction": "createDocument"}, files=files)

        call_kwargs = http.request.call_args[1]
        assert call_kwargs["files"] == files
        assert call_kwargs["data"] == {"cmisaction": "createDocument"}

    def test_post_form_with_tenant(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(201)

        inv.post_form("/path", data={"a": "b"}, tenant_subdomain="tenant-x")

        call_kwargs = http.request.call_args[1]
        assert call_kwargs["tenant_subdomain"] == "tenant-x"

    def test_post_form_500_raises_runtime(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(500, text="Internal Server Error")

        with pytest.raises(DMSRuntimeException) as exc_info:
            inv.post_form("/path", data={})
        assert exc_info.value.status_code == 500

    def test_post_form_204_returns_response(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(204)

        result = inv.post_form("/path", data={})
        assert result.status_code == 204


# ---------------------------------------------------------------
# get_stream
# ---------------------------------------------------------------


class TestGetStream:
    def test_returns_raw_response(self, invoker):
        inv, http = invoker
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.content = b"binary content"
        http.request.return_value = mock_resp

        result = inv.get_stream(
            "/browser/repo1/root", params={"objectId": "d1", "cmisselector": "content"}
        )

        assert result is mock_resp
        http.request.assert_called_once()
        call_kwargs = http.request.call_args[1]
        assert call_kwargs["stream"] is True
        assert call_kwargs["params"] == {"objectId": "d1", "cmisselector": "content"}

    def test_raises_on_error(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(404, text="Not found")

        with pytest.raises(DMSObjectNotFoundException) as exc_info:
            inv.get_stream(
                "/browser/repo1/root",
                params={"objectId": "d1", "cmisselector": "content"},
            )
        assert exc_info.value.status_code == 404

    def test_passes_tenant_subdomain(self, invoker):
        inv, http = invoker
        http.request.return_value = _make_response(200)

        inv.get_stream("/path", tenant_subdomain="sub1")

        assert http.request.call_args[1]["tenant_subdomain"] == "sub1"
