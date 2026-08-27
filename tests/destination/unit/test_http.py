"""Unit tests for _dest_request helper."""

import pytest
from unittest.mock import MagicMock
from requests import Response
from requests.exceptions import RequestException

from sap_cloud_sdk.core._http_client import HttpClient, HttpMethod
from sap_cloud_sdk.destination._http import _request
from sap_cloud_sdk.destination.exceptions import HttpError


def _mock_http(status: int = 200, text: str = "") -> tuple[MagicMock, MagicMock]:
    http = MagicMock(spec=HttpClient)
    resp = MagicMock(spec=Response)
    resp.status_code = status
    resp.text = text
    http.request.return_value = resp
    return http, resp


class TestRequest:

    def test_get_injects_accept_header_and_normalizes_path(self):
        http, resp = _mock_http(200)

        result = _request(http, HttpMethod.GET, "v1/instanceDestinations/my-dest", tenant_subdomain="tenant-1")

        assert result is resp
        http.request.assert_called_once_with(
            HttpMethod.GET,
            "/v1/instanceDestinations/my-dest",
            tenant_subdomain="tenant-1",
            params=None,
            json=None,
            headers={"Accept": "application/json"},
        )

    def test_path_with_leading_slash_not_doubled(self):
        http, _ = _mock_http(200)

        _request(http, HttpMethod.GET, "/v1/subaccountDestinations")

        call_args = http.request.call_args
        assert call_args[0][1] == "/v1/subaccountDestinations"

    def test_post_passes_json_body(self):
        http, _ = _mock_http(201)
        body = {"Name": "my-dest", "URL": "https://api.example.com"}

        _request(http, HttpMethod.POST, "v1/subaccountDestinations", json=body)

        call_args = http.request.call_args
        assert call_args[1]["json"] == body

    def test_extra_headers_merged_with_accept(self):
        http, _ = _mock_http(200)

        _request(http, HttpMethod.GET, "v1/foo", headers={"X-Custom": "val"})

        call_args = http.request.call_args
        assert call_args[1]["headers"] == {"Accept": "application/json", "X-Custom": "val"}

    def test_non_2xx_raises_http_error_with_status_and_text(self):
        http, _ = _mock_http(404, "Not Found")

        with pytest.raises(HttpError) as exc:
            _request(http, HttpMethod.GET, "instanceDestinations/unknown")

        err = exc.value
        assert err.status_code == 404
        assert "Not Found" in err.response_text  # ty: ignore[unsupported-operator]
        assert "HTTP 404 for GET" in str(err)

    def test_500_error_raises_http_error(self):
        http, _ = _mock_http(500, "Internal Server Error")

        with pytest.raises(HttpError) as exc:
            _request(http, HttpMethod.POST, "v1/subaccountDestinations", json={})

        assert exc.value.status_code == 500

    def test_request_exception_wrapped_in_http_error(self):
        http = MagicMock(spec=HttpClient)
        http.request.side_effect = RequestException("connection refused")

        with pytest.raises(HttpError, match="request failed: connection refused"):
            _request(http, HttpMethod.GET, "any/path")

    def test_tenant_subdomain_forwarded(self):
        http, _ = _mock_http(200)

        _request(http, HttpMethod.GET, "v1/foo", tenant_subdomain="subscriber-abc")

        call_args = http.request.call_args
        assert call_args[1]["tenant_subdomain"] == "subscriber-abc"

    def test_params_forwarded(self):
        http, _ = _mock_http(200)
        params = {"$filter": "Name eq 'dest'"}

        _request(http, HttpMethod.GET, "v1/subaccountDestinations", params=params)

        call_args = http.request.call_args
        assert call_args[1]["params"] == params
