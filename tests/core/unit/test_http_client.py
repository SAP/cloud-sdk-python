"""Tests for HttpClient and XsuaaAuthProvider."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from sap_cloud_sdk.core._http_client import HttpClient, HttpMethod, XsuaaAuthProvider


def _make_response(status_code: int) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    return resp


def _make_mock_auth(base_url: str | None = None) -> MagicMock:
    """Return a mock AuthProvider with base_url set to None by default.

    Without an explicit assignment, MagicMock(spec=...) returns a truthy
    MagicMock for the base_url attribute, which would override the constructor
    URL in HttpClient._execute.  Setting it to None lets the fallback logic
    use the URL passed to the HttpClient constructor.
    """
    auth = MagicMock(spec=XsuaaAuthProvider)
    auth.base_url = base_url
    return auth


def _make_client_with_mock_session(
    base_url: str = "https://example.com",
    status_code: int = 200,
) -> tuple[HttpClient, MagicMock, MagicMock]:
    auth = _make_mock_auth()
    session = MagicMock()
    session.request.return_value = _make_response(status_code)
    auth.get_session.return_value = session
    return HttpClient(base_url, auth), auth, session


class TestHttpClient:
    # ── 401 retry ──────────────────────────────────────────────────────────────

    def test_401_triggers_invalidate_and_retry(self):
        auth = _make_mock_auth()
        session = MagicMock()
        auth.get_session.return_value = session

        first = _make_response(401)
        second = _make_response(200)
        session.request.side_effect = [first, second]

        client = HttpClient("https://example.com", auth)
        result = client.request(HttpMethod.GET, "/data")

        assert result.status_code == 200
        auth.invalidate.assert_called_once_with(None)
        assert session.request.call_count == 2

    def test_401_without_auth_provider_is_not_retried(self):
        client = HttpClient("https://example.com", auth_provider=None)
        with patch("requests.Session.request", return_value=_make_response(401)) as mock_req:
            result = client.request(HttpMethod.GET, "/data")
        assert result.status_code == 401
        assert mock_req.call_count == 1

    def test_200_response_not_retried(self):
        client, auth, session = _make_client_with_mock_session()
        result = client.request(HttpMethod.GET, "/data")
        assert result.status_code == 200
        auth.invalidate.assert_not_called()
        assert session.request.call_count == 1

    def test_retry_uses_fresh_session_after_invalidate(self):
        auth = _make_mock_auth()
        stale_session = MagicMock()
        fresh_session = MagicMock()

        stale_session.request.return_value = _make_response(401)
        fresh_session.request.return_value = _make_response(200)
        auth.get_session.side_effect = [stale_session, fresh_session]

        client = HttpClient("https://example.com", auth)
        result = client.request(HttpMethod.GET, "/data", tenant_subdomain="acme")

        assert result.status_code == 200
        auth.invalidate.assert_called_once_with("acme")
        auth.get_session.assert_called_with("acme")

    # ── Non-401 status codes are returned as-is (no retry) ────────────────────

    @pytest.mark.parametrize("status_code", [400, 403, 404, 409, 500, 503])
    def test_non_401_error_not_retried(self, status_code: int):
        client, auth, session = _make_client_with_mock_session(status_code=status_code)
        result = client.request(HttpMethod.GET, "/resource")
        assert result.status_code == status_code
        auth.invalidate.assert_not_called()
        assert session.request.call_count == 1

    # ── HTTP methods ───────────────────────────────────────────────────────────

    @pytest.mark.parametrize("method", [
        HttpMethod.GET,
        HttpMethod.POST,
        HttpMethod.PUT,
        HttpMethod.PATCH,
        HttpMethod.DELETE,
    ])
    def test_all_http_methods_forwarded(self, method: HttpMethod):
        client, _, session = _make_client_with_mock_session()
        client.request(method, "/endpoint")
        session.request.assert_called_once()
        assert session.request.call_args[0][0] == method.value

    def test_string_method_uppercased(self):
        client, _, session = _make_client_with_mock_session()
        client.request("get", "/resource")
        assert session.request.call_args[0][0] == "GET"

    # ── URL construction ───────────────────────────────────────────────────────

    def test_path_appended_to_base_url(self):
        client, _, session = _make_client_with_mock_session("https://svc.example.com")
        client.request(HttpMethod.GET, "/v1/memories")
        assert session.request.call_args[0][1] == "https://svc.example.com/v1/memories"

    def test_base_url_trailing_slash_stripped(self):
        client, _, session = _make_client_with_mock_session("https://svc.example.com/")
        client.request(HttpMethod.GET, "/items")
        assert session.request.call_args[0][1] == "https://svc.example.com/items"

    def test_rotated_base_url_used_after_token_refresh(self):
        """Requests use auth_provider.base_url (updated on token refresh) not the stale constructor URL."""
        auth = _make_mock_auth(base_url="https://new-svc.example.com")
        session = MagicMock()
        session.request.return_value = _make_response(200)
        auth.get_session.return_value = session

        client = HttpClient("https://old-svc.example.com", auth)
        client.request(HttpMethod.GET, "/v1/memories")

        assert session.request.call_args[0][1] == "https://new-svc.example.com/v1/memories"

    def test_falls_back_to_constructor_url_when_provider_base_url_is_none(self):
        """When auth_provider.base_url is None, the constructor URL is used."""
        client, _, session = _make_client_with_mock_session("https://svc.example.com")
        client.request(HttpMethod.GET, "/items")
        assert session.request.call_args[0][1] == "https://svc.example.com/items"

    # ── kwargs forwarding ──────────────────────────────────────────────────────

    def test_json_body_forwarded(self):
        client, _, session = _make_client_with_mock_session()
        client.request(HttpMethod.POST, "/items", json={"key": "value"})
        assert session.request.call_args[1]["json"] == {"key": "value"}

    def test_params_forwarded(self):
        client, _, session = _make_client_with_mock_session()
        client.request(HttpMethod.GET, "/items", params={"$top": "10"})
        assert session.request.call_args[1]["params"] == {"$top": "10"}

    def test_headers_forwarded(self):
        client, _, session = _make_client_with_mock_session()
        client.request(HttpMethod.GET, "/items", headers={"Accept": "application/json"})
        assert session.request.call_args[1]["headers"] == {"Accept": "application/json"}

    # ── Timeout ────────────────────────────────────────────────────────────────

    def test_default_timeout_passed_to_session(self):
        client, _, session = _make_client_with_mock_session()
        client.request(HttpMethod.GET, "/data")
        assert session.request.call_args[1]["timeout"] == 30.0

    def test_custom_timeout_passed_to_session(self):
        auth = _make_mock_auth()
        session = MagicMock()
        session.request.return_value = _make_response(200)
        auth.get_session.return_value = session
        client = HttpClient("https://example.com", auth, timeout=5.0)
        client.request(HttpMethod.GET, "/data")
        assert session.request.call_args[1]["timeout"] == 5.0

    # ── Tenant subdomain ───────────────────────────────────────────────────────

    def test_tenant_subdomain_forwarded_to_auth_provider(self):
        client, auth, _ = _make_client_with_mock_session()
        client.request(HttpMethod.GET, "/data", tenant_subdomain="my-tenant")
        auth.get_session.assert_called_with("my-tenant")

    # ── No-auth mode ───────────────────────────────────────────────────────────

    def test_no_auth_uses_plain_session(self):
        client = HttpClient("https://example.com", auth_provider=None)
        with patch.object(requests.Session, "request", return_value=_make_response(200)) as mock_req:
            result = client.request(HttpMethod.GET, "/public")
        assert result.status_code == 200
        mock_req.assert_called_once()

    def test_no_auth_plain_session_reused(self):
        client = HttpClient("https://example.com", auth_provider=None)
        with patch.object(requests.Session, "request", return_value=_make_response(200)):
            client.request(HttpMethod.GET, "/a")
            client.request(HttpMethod.GET, "/b")
        assert client._plain_session is not None

    # ── close() ────────────────────────────────────────────────────────────────

    def test_close_calls_auth_provider_close(self):
        client, auth, _ = _make_client_with_mock_session()
        client.close()
        auth.close.assert_called_once()

    def test_close_no_auth_closes_plain_session(self):
        client = HttpClient("https://example.com", auth_provider=None)
        mock_session = MagicMock()
        client._plain_session = mock_session
        client.close()
        mock_session.close.assert_called_once()
        assert client._plain_session is None
