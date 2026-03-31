"""Unit tests for HttpInvoker (get, post_form, get_stream, header methods)."""

from unittest.mock import Mock, patch

import pytest
import requests

from sap_cloud_sdk.dms._http import HttpInvoker
from sap_cloud_sdk.dms.exceptions import (
    DMSConflictException,
    DMSConnectionError,
    DMSInvalidArgumentException,
    DMSObjectNotFoundException,
    DMSPermissionDeniedException,
    DMSRuntimeException,
)


@pytest.fixture
def mock_auth():
    auth = Mock()
    auth.get_token.return_value = "test-token-123"
    return auth


@pytest.fixture
def invoker(mock_auth):
    return HttpInvoker(
        auth=mock_auth,
        base_url="https://api.example.com",
        connect_timeout=5,
        read_timeout=15,
    )


# ---------------------------------------------------------------
# Header helpers
# ---------------------------------------------------------------

class TestHeaders:
    def test_auth_header(self, invoker):
        headers = invoker._auth_header()
        assert headers == {"Authorization": "Bearer test-token-123"}

    def test_auth_header_with_tenant(self, invoker, mock_auth):
        invoker._auth_header("tenant-sub")
        mock_auth.get_token.assert_called_with("tenant-sub")

    def test_default_headers(self, invoker):
        headers = invoker._default_headers()
        assert headers["Authorization"] == "Bearer test-token-123"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_merged_headers_applies_overrides(self, invoker):
        merged = invoker._merged_headers(None, {"Accept": "text/xml"})
        assert merged["Accept"] == "text/xml"
        assert merged["Authorization"] == "Bearer test-token-123"


# ---------------------------------------------------------------
# GET
# ---------------------------------------------------------------

class TestGet:
    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_basic(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"key": "val"}'
        mock_resp.json.return_value = {"key": "val"}
        mock_get.return_value = mock_resp

        result = invoker.get("/rest/v2/repos")

        mock_get.assert_called_once_with(
            "https://api.example.com/rest/v2/repos",
            headers={
                "Authorization": "Bearer test-token-123",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            params=None,
            timeout=(5, 15),
        )
        assert result is mock_resp

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_with_params(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        result = invoker.get("/path", params={"objectId": "abc", "cmisselector": "acl"})

        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"] == {"objectId": "abc", "cmisselector": "acl"}
        assert result is mock_resp

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_with_custom_headers(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        invoker.get("/repos", headers={"Accept": "application/vnd.sap.sdm+json"})

        call_kwargs = mock_get.call_args[1]
        # Custom Accept should override default
        assert call_kwargs["headers"]["Accept"] == "application/vnd.sap.sdm+json"
        # Auth should still be present
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-token-123"

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_with_tenant(self, mock_get, invoker, mock_auth):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        invoker.get("/path", tenant_subdomain="sub1")

        mock_auth.get_token.assert_called_with("sub1")

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_404_raises_not_found(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_resp

        with pytest.raises(DMSObjectNotFoundException) as exc_info:
            invoker.get("/missing")
        assert exc_info.value.status_code == 404

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_400_raises_invalid_argument(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_resp

        with pytest.raises(DMSInvalidArgumentException) as exc_info:
            invoker.get("/bad")
        assert exc_info.value.status_code == 400

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_401_raises_permission_denied(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_resp

        with pytest.raises(DMSPermissionDeniedException) as exc_info:
            invoker.get("/unauthorized")
        assert exc_info.value.status_code == 401

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_500_raises_runtime(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_resp

        with pytest.raises(DMSRuntimeException) as exc_info:
            invoker.get("/error")
        assert exc_info.value.status_code == 500

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_connection_error(self, mock_get, invoker):
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")

        with pytest.raises(DMSConnectionError):
            invoker.get("/unreachable")

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_get_timeout_error(self, mock_get, invoker):
        mock_get.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(DMSConnectionError):
            invoker.get("/slow")


# ---------------------------------------------------------------
# Error message extraction
# ---------------------------------------------------------------

class TestErrorMessageExtraction:
    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_400_extracts_json_message(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 400
        mock_resp.text = '{"exception": "versioning", "message": "The object is not the latest version"}'
        mock_resp.json.return_value = {
            "exception": "versioning",
            "message": "The object is not the latest version",
        }
        mock_get.return_value = mock_resp

        with pytest.raises(DMSInvalidArgumentException) as exc_info:
            invoker.get("/bad")
        assert "The object is not the latest version" in str(exc_info.value)

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_400_fallback_when_no_json(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_resp

        with pytest.raises(DMSInvalidArgumentException) as exc_info:
            invoker.get("/bad")
        assert "Request contains invalid or disallowed parameters" in str(exc_info.value)

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_404_extracts_json_message(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_resp.text = '{"message": "Document abc-123 not found"}'
        mock_resp.json.return_value = {"message": "Document abc-123 not found"}
        mock_get.return_value = mock_resp

        with pytest.raises(DMSObjectNotFoundException) as exc_info:
            invoker.get("/missing")
        assert "Document abc-123 not found" in str(exc_info.value)

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_409_raises_conflict(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 409
        mock_resp.text = '{"exception": "versioning", "message": "Object already exists with name test.txt"}'
        mock_resp.json.return_value = {
            "exception": "versioning",
            "message": "Object already exists with name test.txt",
        }
        mock_get.return_value = mock_resp

        with pytest.raises(DMSConflictException) as exc_info:
            invoker.get("/conflict")
        assert exc_info.value.status_code == 409
        assert "Object already exists with name test.txt" in str(exc_info.value)

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_409_fallback_when_no_json(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 409
        mock_resp.text = "Conflict"
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_resp

        with pytest.raises(DMSConflictException) as exc_info:
            invoker.get("/conflict")
        assert "conflicts with the current state" in str(exc_info.value)


# ---------------------------------------------------------------
# POST (form-encoded)
# ---------------------------------------------------------------

class TestPostForm:
    @patch("sap_cloud_sdk.dms._http.requests.post")
    def test_post_form_basic(self, mock_post, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_resp.content = b'{"succinctProperties": {}}'
        mock_resp.json.return_value = {"succinctProperties": {}}
        mock_post.return_value = mock_resp

        form = {"cmisaction": "createFolder", "objectId": "root-id"}
        result = invoker.post_form("/browser/repo1/root", data=form)

        mock_post.assert_called_once_with(
            "https://api.example.com/browser/repo1/root",
            headers={"Authorization": "Bearer test-token-123"},
            data=form,
            files=None,
            timeout=(5, 15),
        )
        assert result is mock_resp

    @patch("sap_cloud_sdk.dms._http.requests.post")
    def test_post_form_no_content_type_header(self, mock_post, invoker):
        """post_form must NOT set Content-Type — let requests handle it."""
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_post.return_value = mock_resp

        invoker.post_form("/path", data={"key": "val"})

        headers_sent = mock_post.call_args[1]["headers"]
        assert "Content-Type" not in headers_sent

    @patch("sap_cloud_sdk.dms._http.requests.post")
    def test_post_form_with_files(self, mock_post, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_post.return_value = mock_resp

        files = {"media": ("test.pdf", b"content", "application/pdf")}
        invoker.post_form("/path", data={"cmisaction": "createDocument"}, files=files)

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["files"] == files
        assert call_kwargs["data"] == {"cmisaction": "createDocument"}

    @patch("sap_cloud_sdk.dms._http.requests.post")
    def test_post_form_with_tenant(self, mock_post, invoker, mock_auth):
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_post.return_value = mock_resp

        invoker.post_form("/path", data={"a": "b"}, tenant_subdomain="tenant-x")

        mock_auth.get_token.assert_called_with("tenant-x")

    @patch("sap_cloud_sdk.dms._http.requests.post")
    def test_post_form_500_raises_runtime(self, mock_post, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_post.return_value = mock_resp

        with pytest.raises(DMSRuntimeException) as exc_info:
            invoker.post_form("/path", data={})
        assert exc_info.value.status_code == 500

    @patch("sap_cloud_sdk.dms._http.requests.post")
    def test_post_form_204_returns_response(self, mock_post, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 204
        mock_resp.content = b""
        mock_post.return_value = mock_resp

        result = invoker.post_form("/path", data={})
        assert result is mock_resp


# ---------------------------------------------------------------
# Base URL stripping
# ---------------------------------------------------------------

class TestBaseUrl:
    def test_trailing_slash_stripped(self, mock_auth):
        inv = HttpInvoker(
            auth=mock_auth,
            base_url="https://api.example.com/",
        )
        assert inv._base_url == "https://api.example.com"


# ---------------------------------------------------------------
# get_stream
# ---------------------------------------------------------------

class TestGetStream:
    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_returns_raw_response(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.content = b"binary content"
        mock_get.return_value = mock_resp

        result = invoker.get_stream("/browser/repo1/root", params={"objectId": "d1", "cmisselector": "content"})

        assert result is mock_resp
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["stream"] is True
        assert call_kwargs[1]["params"] == {"objectId": "d1", "cmisselector": "content"}

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_raises_on_error(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_get.return_value = mock_resp

        with pytest.raises(DMSObjectNotFoundException) as exc_info:
            invoker.get_stream("/browser/repo1/root", params={"objectId": "d1", "cmisselector": "content"})
        assert exc_info.value.status_code == 404

    @patch("sap_cloud_sdk.dms._http.requests.get")
    def test_uses_auth_headers(self, mock_get, invoker):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.content = b"data"
        mock_get.return_value = mock_resp

        invoker.get_stream("/path")

        headers = mock_get.call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token-123"
