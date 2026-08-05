"""Unit tests for HttpTransport."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.agent_memory._http_transport import (
    HttpTransport,
    _TOKEN_EXPIRY_BUFFER_SECONDS,
)
from sap_cloud_sdk.agent_memory.config import AgentMemoryConfig
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryHttpError, AgentMemoryNotFoundError


def _config(
    with_auth: bool = True,
    identityzone: str | None = None,
    token_url: str = "http://auth.example.com/oauth/token",
) -> AgentMemoryConfig:
    if with_auth:
        return AgentMemoryConfig(
            base_url="http://localhost:8080",
            token_url=token_url,
            client_id="client-id",
            client_secret="client-secret",
            identityzone=identityzone,
        )
    return AgentMemoryConfig(base_url="http://localhost:8080")


def _mock_response(
    status_code: int,
    json_data: dict | None = None,
    text: str = "",
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.content = b"content" if json_data is not None else b""
    response.text = text
    response.json.return_value = json_data or {}
    return response


# ── No-auth local dev mode ────────────────────────────────────────────────────


class TestNoAuthMode:

    def test_sends_request_without_authorization_header(self):
        """No-auth mode does not send an Authorization header."""
        transport = HttpTransport(_config(with_auth=False))
        mock_session = MagicMock()
        transport._plain_session = mock_session
        mock_session.request.return_value = _mock_response(200, {"data": []})

        transport.get("/test")

        _, kwargs = mock_session.request.call_args
        assert "Authorization" not in kwargs.get("headers", {})

    def test_uses_plain_session_when_no_token_url(self):
        """No-auth mode uses a plain requests.Session, not OAuth2Session."""
        with patch("sap_cloud_sdk.agent_memory._http_transport.requests") as mock_requests:
            mock_session = MagicMock()
            mock_requests.Session.return_value = mock_session
            mock_session.request.return_value = _mock_response(200, {})

            transport = HttpTransport(_config(with_auth=False))
            transport.get("/test")

        mock_requests.Session.assert_called_once()


# ── Token acquisition ─────────────────────────────────────────────────────────


class TestTokenAcquisition:

    def test_token_is_fetched_and_cached(self):
        """fetch_token is called only once across multiple requests with the same tenant."""
        with patch(
            "sap_cloud_sdk.agent_memory._http_transport.OAuth2Session"
        ) as MockOAuth, patch(
            "sap_cloud_sdk.agent_memory._http_transport.BackendApplicationClient"
        ):
            mock_oauth = MagicMock()
            MockOAuth.return_value = mock_oauth
            mock_oauth.fetch_token.return_value = {
                "access_token": "my-token",
                "expires_in": 3600,
            }
            mock_oauth.request.return_value = _mock_response(200, {"data": []})

            transport = HttpTransport(_config())
            transport.get("/test")
            transport.get("/test")

        assert mock_oauth.fetch_token.call_count == 1

    def test_expired_token_triggers_refetch(self):
        """Expired token causes a new fetch_token call."""
        with patch(
            "sap_cloud_sdk.agent_memory._http_transport.OAuth2Session"
        ) as MockOAuth, patch(
            "sap_cloud_sdk.agent_memory._http_transport.BackendApplicationClient"
        ):
            mock_oauth = MagicMock()
            MockOAuth.return_value = mock_oauth
            mock_oauth.fetch_token.return_value = {
                "access_token": "token",
                "expires_in": 3600,
            }
            mock_oauth.request.return_value = _mock_response(200, {})

            transport = HttpTransport(_config())
            # Force the cache to have an expired entry
            past = datetime.now() - timedelta(seconds=1)
            transport._oauth_cache[None] = (mock_oauth, past)
            transport.get("/test")

        assert mock_oauth.fetch_token.call_count >= 1

    def test_token_expiry_uses_buffer(self):
        """Token expiry is set with _TOKEN_EXPIRY_BUFFER_SECONDS subtracted."""
        with patch(
            "sap_cloud_sdk.agent_memory._http_transport.OAuth2Session"
        ) as MockOAuth, patch(
            "sap_cloud_sdk.agent_memory._http_transport.BackendApplicationClient"
        ):
            mock_oauth = MagicMock()
            MockOAuth.return_value = mock_oauth
            mock_oauth.fetch_token.return_value = {
                "access_token": "tok",
                "expires_in": 3600,
            }
            mock_oauth.request.return_value = _mock_response(200, {})

            transport = HttpTransport(_config())
            transport.get("/test")

        _, expires_at = transport._oauth_cache[None]
        expected_max = datetime.now() + timedelta(
            seconds=3600 - _TOKEN_EXPIRY_BUFFER_SECONDS + 5
        )
        assert expires_at < expected_max

    def test_token_fetch_failure_raises_http_error(self):
        """Failed token fetch raises AgentMemoryHttpError."""
        with patch(
            "sap_cloud_sdk.agent_memory._http_transport.OAuth2Session"
        ) as MockOAuth, patch(
            "sap_cloud_sdk.agent_memory._http_transport.BackendApplicationClient"
        ):
            mock_oauth = MagicMock()
            MockOAuth.return_value = mock_oauth
            mock_oauth.fetch_token.side_effect = Exception("connection refused")

            transport = HttpTransport(_config())
            with pytest.raises(AgentMemoryHttpError, match="OAuth2 token"):
                transport.get("/test")


# ── Per-tenant token derivation ───────────────────────────────────────────────


class TestTenantTokenDerivation:

    def test_subscriber_token_url_replaces_identityzone(self):
        """When tenant_subdomain is provided, identityzone is replaced in the token URL."""
        token_url = "http://provider-zone.auth.example.com/oauth/token"
        cfg = _config(with_auth=True, identityzone="provider-zone", token_url=token_url)

        captured_urls = []

        def fake_fetch_token(**kwargs):
            captured_urls.append(kwargs["token_url"])
            return {"access_token": "tok", "expires_in": 3600}

        with patch(
            "sap_cloud_sdk.agent_memory._http_transport.OAuth2Session"
        ) as MockOAuth, patch(
            "sap_cloud_sdk.agent_memory._http_transport.BackendApplicationClient"
        ):
            mock_oauth = MagicMock()
            MockOAuth.return_value = mock_oauth
            mock_oauth.fetch_token.side_effect = fake_fetch_token
            mock_oauth.request.return_value = _mock_response(200, {})

            transport = HttpTransport(cfg)
            transport.get("/test", tenant_subdomain="subscriber-zone")

        assert len(captured_urls) == 1
        assert "subscriber-zone" in captured_urls[0]
        assert "provider-zone" not in captured_urls[0]

    def test_provider_token_url_unchanged_when_no_tenant(self):
        """Without tenant_subdomain, the provider token URL is used as-is."""
        token_url = "http://provider-zone.auth.example.com/oauth/token"
        cfg = _config(with_auth=True, identityzone="provider-zone", token_url=token_url)

        captured_urls = []

        def fake_fetch_token(**kwargs):
            captured_urls.append(kwargs["token_url"])
            return {"access_token": "tok", "expires_in": 3600}

        with patch(
            "sap_cloud_sdk.agent_memory._http_transport.OAuth2Session"
        ) as MockOAuth, patch(
            "sap_cloud_sdk.agent_memory._http_transport.BackendApplicationClient"
        ):
            mock_oauth = MagicMock()
            MockOAuth.return_value = mock_oauth
            mock_oauth.fetch_token.side_effect = fake_fetch_token
            mock_oauth.request.return_value = _mock_response(200, {})

            transport = HttpTransport(cfg)
            transport.get("/test")  # no tenant_subdomain → None

        assert captured_urls[0] == token_url

    def test_tokens_cached_independently_per_tenant(self):
        """Provider and subscriber tokens are cached under separate keys."""
        token_url = "http://prov.auth.example.com/oauth/token"
        cfg = _config(with_auth=True, identityzone="prov", token_url=token_url)

        with patch(
            "sap_cloud_sdk.agent_memory._http_transport.OAuth2Session"
        ) as MockOAuth, patch(
            "sap_cloud_sdk.agent_memory._http_transport.BackendApplicationClient"
        ):
            mock_oauth = MagicMock()
            MockOAuth.return_value = mock_oauth
            mock_oauth.fetch_token.return_value = {"access_token": "tok", "expires_in": 3600}
            mock_oauth.request.return_value = _mock_response(200, {})

            transport = HttpTransport(cfg)
            transport.get("/test")                          # provider (None)
            transport.get("/test", tenant_subdomain="sub")  # subscriber

        assert None in transport._oauth_cache
        assert "sub" in transport._oauth_cache
        assert mock_oauth.fetch_token.call_count == 2

    def test_subscriber_token_reused_on_second_call(self):
        """Subscriber token is cached and not re-fetched on a second call."""
        token_url = "http://prov.auth.example.com/oauth/token"
        cfg = _config(with_auth=True, identityzone="prov", token_url=token_url)

        with patch(
            "sap_cloud_sdk.agent_memory._http_transport.OAuth2Session"
        ) as MockOAuth, patch(
            "sap_cloud_sdk.agent_memory._http_transport.BackendApplicationClient"
        ):
            mock_oauth = MagicMock()
            MockOAuth.return_value = mock_oauth
            mock_oauth.fetch_token.return_value = {"access_token": "tok", "expires_in": 3600}
            mock_oauth.request.return_value = _mock_response(200, {})

            transport = HttpTransport(cfg)
            transport.get("/test", tenant_subdomain="sub")
            transport.get("/test", tenant_subdomain="sub")

        assert mock_oauth.fetch_token.call_count == 1


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:

    def _transport_no_auth(self) -> tuple[HttpTransport, MagicMock]:
        transport = HttpTransport(_config(with_auth=False))
        mock_session = MagicMock()
        transport._plain_session = mock_session
        return transport, mock_session

    def test_get_sends_get_request(self):
        """GET request is constructed with the correct method and URL."""
        transport, mock_session = self._transport_no_auth()
        mock_session.request.return_value = _mock_response(200, {"key": "value"})

        result = transport.get("/memories", params={"$top": "10"})

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1].startswith("http://localhost:8080/memories")
        assert "%24top=10" in call_args[0][1]
        assert result == {"key": "value"}

    def test_post_sends_post_request(self):
        """POST request is constructed with the correct method."""
        transport, mock_session = self._transport_no_auth()
        mock_session.request.return_value = _mock_response(201, {"id": "new-memory"})

        result = transport.post("/memories", json={"agentID": "a"})

        assert mock_session.request.call_args[0][0] == "POST"
        assert result == {"id": "new-memory"}

    def test_patch_sends_patch_request(self):
        """PATCH request is constructed with the correct method."""
        transport, mock_session = self._transport_no_auth()
        mock_session.request.return_value = _mock_response(200, {"id": "mem-1"})

        result = transport.patch("/memories(mem-1)", json={"content": "updated"})

        assert mock_session.request.call_args[0][0] == "PATCH"
        assert result == {"id": "mem-1"}

    def test_delete_sends_delete_and_returns_none(self):
        """DELETE sends correct method and returns None."""
        transport, mock_session = self._transport_no_auth()
        mock_session.request.return_value = _mock_response(204)

        result = transport.delete("/memories/abc")

        assert mock_session.request.call_args[0][0] == "DELETE"
        assert result is None

    def test_404_raises_not_found_error(self):
        """404 responses raise AgentMemoryNotFoundError."""
        transport, mock_session = self._transport_no_auth()
        mock_resp = _mock_response(404, text="Not Found")
        mock_resp.content = b"Not Found"
        mock_session.request.return_value = mock_resp

        with pytest.raises(AgentMemoryNotFoundError) as exc_info:
            transport.get("/memories/nonexistent")

        assert exc_info.value.status_code == 404

    def test_server_error_raises_http_error(self):
        """500 responses raise AgentMemoryHttpError with the status code."""
        transport, mock_session = self._transport_no_auth()
        mock_resp = _mock_response(500, text="Internal Server Error")
        mock_resp.content = b"Internal Server Error"
        mock_session.request.return_value = mock_resp

        with pytest.raises(AgentMemoryHttpError) as exc_info:
            transport.get("/memories")

        assert exc_info.value.status_code == 500


# ── Close ─────────────────────────────────────────────────────────────────────


class TestClose:

    def test_close_clears_all_oauth_sessions(self):
        """close() closes all cached OAuth sessions."""
        with patch(
            "sap_cloud_sdk.agent_memory._http_transport.OAuth2Session"
        ) as MockOAuth, patch(
            "sap_cloud_sdk.agent_memory._http_transport.BackendApplicationClient"
        ):
            mock_oauth = MagicMock()
            MockOAuth.return_value = mock_oauth
            mock_oauth.fetch_token.return_value = {"access_token": "tok", "expires_in": 3600}
            mock_oauth.request.return_value = _mock_response(200, {})

            token_url = "http://prov.auth.example.com/oauth/token"
            cfg = _config(with_auth=True, identityzone="prov", token_url=token_url)
            transport = HttpTransport(cfg)
            transport.get("/test")                          # provider
            transport.get("/test", tenant_subdomain="sub")  # subscriber
            transport.close()

        assert mock_oauth.close.call_count == 2
        assert len(transport._oauth_cache) == 0

    def test_close_clears_plain_session(self):
        """close() clears the plain session in no-auth mode."""
        transport = HttpTransport(_config(with_auth=False))
        mock_session = MagicMock()
        transport._plain_session = mock_session

        transport.close()

        mock_session.close.assert_called_once()
        assert transport._plain_session is None
