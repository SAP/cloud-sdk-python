"""Unit tests for DestinationHttpClient."""

from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.destination._destination_http_client import DestinationHttpClient
from sap_cloud_sdk.destination._models import AuthToken, Destination


def _dest(**kwargs) -> Destination:
    base = {"Name": "test", "Type": "HTTP", "URL": "https://example.com"}
    base.update(kwargs)
    return Destination.from_dict(base)


def _auth_token(key: str, value: str) -> AuthToken:
    return AuthToken(type="Bearer", value="raw", http_header={"key": key, "value": value})


class TestDestinationHttpClientInit:
    def test_raises_for_non_http_destination(self):
        dest = Destination.from_dict({"Name": "test", "Type": "RFC"})
        with pytest.raises(ValueError, match="only supports HTTP destinations"):
            DestinationHttpClient(dest)

    def test_erp_headers_pre_baked(self):
        dest = _dest(**{"sap-client": "100", "sap-language": "en"})
        client = DestinationHttpClient(dest)
        assert client._session.headers["sap-client"] == "100"
        assert client._session.headers["sap-language"] == "en"

    def test_no_erp_headers_when_properties_empty(self):
        dest = _dest()
        client = DestinationHttpClient(dest)
        assert "sap-client" not in client._session.headers
        assert "sap-language" not in client._session.headers

    def test_auth_header_pre_baked_from_auth_tokens(self):
        dest = _dest()
        dest.auth_tokens = [_auth_token("Authorization", "Bearer eyJ123")]
        client = DestinationHttpClient(dest)
        assert client._session.headers["Authorization"] == "Bearer eyJ123"

    def test_multiple_auth_tokens_all_injected(self):
        dest = _dest()
        dest.auth_tokens = [
            _auth_token("Authorization", "Bearer eyJ123"),
            _auth_token("x-sap-security-session", "mysession"),
        ]
        client = DestinationHttpClient(dest)
        assert client._session.headers["Authorization"] == "Bearer eyJ123"
        assert client._session.headers["x-sap-security-session"] == "mysession"

    def test_error_token_with_empty_values_is_skipped(self):
        dest = _dest()
        dest.auth_tokens = [_auth_token("", "")]
        client = DestinationHttpClient(dest)
        assert "Authorization" not in client._session.headers

    def test_no_auth_header_when_auth_tokens_empty(self):
        dest = _dest()
        client = DestinationHttpClient(dest)
        assert "Authorization" not in client._session.headers


class TestDestinationHttpClientRequest:
    def setup_method(self):
        self.dest = _dest()
        self.client = DestinationHttpClient(self.dest)
        self.mock_response = MagicMock()

    def test_constructs_full_url(self):
        with patch.object(self.client._session, "request", return_value=self.mock_response) as mock_req:
            self.client.request("GET", "/api/v1/users")
            assert mock_req.call_args[1]["url"] == "https://example.com/api/v1/users"

    def test_uppercases_method(self):
        with patch.object(self.client._session, "request", return_value=self.mock_response) as mock_req:
            self.client.request("get", "/resource")
            assert mock_req.call_args[1]["method"] == "GET"

    def test_passes_params(self):
        with patch.object(self.client._session, "request", return_value=self.mock_response) as mock_req:
            self.client.request("GET", "/resource", params={"$top": "10"})
            assert mock_req.call_args[1]["params"] == {"$top": "10"}

    def test_passes_json_body(self):
        with patch.object(self.client._session, "request", return_value=self.mock_response) as mock_req:
            self.client.request("POST", "/resource", json={"key": "value"})
            assert mock_req.call_args[1]["json"] == {"key": "value"}

    def test_passes_extra_headers(self):
        with patch.object(self.client._session, "request", return_value=self.mock_response) as mock_req:
            self.client.request("GET", "/resource", headers={"X-Custom": "yes"})
            assert mock_req.call_args[1]["headers"] == {"X-Custom": "yes"}

    def test_returns_response(self):
        with patch.object(self.client._session, "request", return_value=self.mock_response):
            assert self.client.request("GET", "/resource") is self.mock_response


class TestDestinationHttpClientVerbHelpers:
    def setup_method(self):
        self.client = DestinationHttpClient(_dest())
        self.mock_response = MagicMock()

    def _patch(self):
        return patch.object(self.client._session, "request", return_value=self.mock_response)

    def test_get_uses_get_method(self):
        with self._patch() as mock_req:
            self.client.get("/r")
            assert mock_req.call_args[1]["method"] == "GET"

    def test_post_uses_post_method(self):
        with self._patch() as mock_req:
            self.client.post("/r", json={"a": 1})
            assert mock_req.call_args[1]["method"] == "POST"

    def test_put_uses_put_method(self):
        with self._patch() as mock_req:
            self.client.put("/r", json={})
            assert mock_req.call_args[1]["method"] == "PUT"

    def test_patch_uses_patch_method(self):
        with self._patch() as mock_req:
            self.client.patch("/r", json={})
            assert mock_req.call_args[1]["method"] == "PATCH"

    def test_delete_uses_delete_method(self):
        with self._patch() as mock_req:
            self.client.delete("/r")
            assert mock_req.call_args[1]["method"] == "DELETE"
