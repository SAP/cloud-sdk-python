"""Unit tests for DestinationHttpClient."""

import ssl
from unittest.mock import MagicMock, call, patch

import pytest

from sap_cloud_sdk.destination._destination_http_client import (
    _ClientCertAdapter,
    DestinationHttpClient,
    RedirectMode,
)
from sap_cloud_sdk.destination._models import AuthToken, Destination
from sap_cloud_sdk.destination.exceptions import DestinationCertificateError


def _dest(**kwargs) -> Destination:
    base = {"Name": "test", "Type": "HTTP", "URL": "https://example.com"}
    base.update(kwargs)
    return Destination.from_dict(base)


def _auth_token(key: str, value: str) -> AuthToken:
    return AuthToken(
        type="Bearer", value="raw", http_header={"key": key, "value": value}
    )


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

    def test_url_headers_properties_pre_baked(self):
        dest = _dest(**{"URL.headers.apiKey": "secret", "URL.headers.X-Tenant": "acme"})
        client = DestinationHttpClient(dest)
        assert client._session.headers["apiKey"] == "secret"
        assert client._session.headers["X-Tenant"] == "acme"


class TestDestinationHttpClientRequest:
    def setup_method(self):
        self.dest = _dest()
        self.client = DestinationHttpClient(self.dest)
        self.mock_response = MagicMock()

    def test_constructs_full_url(self):
        with patch.object(
            self.client._session, "request", return_value=self.mock_response
        ) as mock_req:
            self.client.request("GET", "/api/v1/users")
            assert mock_req.call_args[1]["url"] == "https://example.com/api/v1/users"

    def test_uppercases_method(self):
        with patch.object(
            self.client._session, "request", return_value=self.mock_response
        ) as mock_req:
            self.client.request("get", "/resource")
            assert mock_req.call_args[1]["method"] == "GET"

    def test_passes_params(self):
        with patch.object(
            self.client._session, "request", return_value=self.mock_response
        ) as mock_req:
            self.client.request("GET", "/resource", params={"$top": "10"})
            assert mock_req.call_args[1]["params"] == {"$top": "10"}

    def test_passes_json_body(self):
        with patch.object(
            self.client._session, "request", return_value=self.mock_response
        ) as mock_req:
            self.client.request("POST", "/resource", json={"key": "value"})
            assert mock_req.call_args[1]["json"] == {"key": "value"}

    def test_passes_extra_headers(self):
        with patch.object(
            self.client._session, "request", return_value=self.mock_response
        ) as mock_req:
            self.client.request("GET", "/resource", headers={"X-Custom": "yes"})
            assert mock_req.call_args[1]["headers"] == {"X-Custom": "yes"}

    def test_returns_response(self):
        with patch.object(
            self.client._session, "request", return_value=self.mock_response
        ):
            assert self.client.request("GET", "/resource") is self.mock_response


class TestDestinationHttpClientCert:
    """Tests that DestinationHttpClient wires the mTLS cert adapter correctly."""

    _PATCH_TARGET = (
        "sap_cloud_sdk.destination._destination_http_client.build_client_cert_context"
    )

    def test_ssl_context_mounts_client_cert_adapter(self):
        """When build_client_cert_context returns a context, https:// uses _ClientCertAdapter."""
        ssl_ctx = ssl.create_default_context()
        with patch(self._PATCH_TARGET, return_value=ssl_ctx):
            client = DestinationHttpClient(_dest())
        assert isinstance(client._session.get_adapter("https://"), _ClientCertAdapter)

    def test_none_context_does_not_mount_client_cert_adapter(self):
        """When build_client_cert_context returns None, https:// uses the default requests adapter."""
        with patch(self._PATCH_TARGET, return_value=None):
            client = DestinationHttpClient(_dest())
        assert not isinstance(
            client._session.get_adapter("https://"), _ClientCertAdapter
        )

    def test_cert_load_error_propagates(self):
        """When build_client_cert_context raises DestinationCertificateError, the constructor propagates it."""
        with patch(self._PATCH_TARGET, side_effect=DestinationCertificateError("boom")):
            with pytest.raises(DestinationCertificateError):
                DestinationHttpClient(_dest())


# ---------------------------------------------------------------------------
# Helpers shared by redirect tests
# ---------------------------------------------------------------------------

def _redirect(status: int, location: str) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.headers = {"Location": location}
    return r


def _ok() -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.headers = {}
    return r


class TestDestinationHttpClientRedirect:
    """Verify redirect-suppression and same-origin enforcement."""

    def setup_method(self):
        self.dest = _dest()
        self.dest.auth_tokens = [
            _auth_token("Authorization", "Bearer secret"),
            _auth_token("x-sap-security-session", "sess-token"),
            _auth_token("apiKey", "k3y"),
        ]

    # ------------------------------------------------------------------
    # Default NONE mode
    # ------------------------------------------------------------------

    def test_default_mode_is_none(self):
        client = DestinationHttpClient(self.dest)
        assert client._redirect_mode is RedirectMode.NONE

    def test_none_does_not_follow_302(self):
        client = DestinationHttpClient(self.dest)
        with patch.object(client._session, "request", return_value=_redirect(302, "/new")) as mock_req:
            resp = client.request("GET", "/old")
        assert resp.status_code == 302
        assert mock_req.call_count == 1
        assert mock_req.call_args.kwargs["allow_redirects"] is False

    @pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
    def test_none_blocks_all_redirect_codes(self, status):
        client = DestinationHttpClient(self.dest)
        with patch.object(client._session, "request", return_value=_redirect(status, "/new")) as mock_req:
            resp = client.request("GET", "/path")
        assert resp.status_code == status
        assert mock_req.call_count == 1

    def test_allow_redirects_kwarg_is_silently_stripped(self):
        client = DestinationHttpClient(self.dest)
        with patch.object(client._session, "request", return_value=_ok()) as mock_req:
            client.request("GET", "/path", allow_redirects=True)
        assert mock_req.call_args.kwargs["allow_redirects"] is False

    def test_credentials_not_forwarded_to_redirect_target(self):
        """In NONE mode the session is only called once — credentials never reach a redirect target."""
        client = DestinationHttpClient(self.dest)
        with patch.object(client._session, "request", return_value=_redirect(302, "https://evil.com/capture")) as mock_req:
            client.request("GET", "/api")
        assert mock_req.call_count == 1  # second origin never receives a call

    # ------------------------------------------------------------------
    # SAME_ORIGIN mode
    # ------------------------------------------------------------------

    def test_same_origin_follows_relative_redirect(self):
        client = DestinationHttpClient(self.dest, redirect_mode=RedirectMode.SAME_ORIGIN)
        with patch.object(client._session, "request", side_effect=[_redirect(302, "/new-path"), _ok()]) as mock_req:
            resp = client.request("GET", "/old-path")
        assert resp.status_code == 200
        assert mock_req.call_count == 2
        assert mock_req.call_args_list[1].kwargs["url"] == "https://example.com/new-path"

    @pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
    def test_same_origin_follows_all_redirect_codes_on_same_host(self, status):
        client = DestinationHttpClient(self.dest, redirect_mode=RedirectMode.SAME_ORIGIN)
        with patch.object(client._session, "request", side_effect=[_redirect(status, "/dest"), _ok()]) as mock_req:
            resp = client.request("GET", "/src")
        assert resp.status_code == 200
        assert mock_req.call_count == 2

    def test_same_origin_rejects_host_change(self):
        client = DestinationHttpClient(self.dest, redirect_mode=RedirectMode.SAME_ORIGIN)
        with patch.object(client._session, "request", side_effect=[_redirect(302, "https://other.com/x")]) as mock_req:
            resp = client.request("GET", "/path")
        assert resp.status_code == 302
        assert mock_req.call_count == 1

    def test_same_origin_rejects_port_change(self):
        client = DestinationHttpClient(self.dest, redirect_mode=RedirectMode.SAME_ORIGIN)
        with patch.object(client._session, "request", side_effect=[_redirect(302, "https://example.com:9443/x")]) as mock_req:
            resp = client.request("GET", "/path")
        assert resp.status_code == 302
        assert mock_req.call_count == 1

    def test_same_origin_rejects_https_to_http_downgrade(self):
        client = DestinationHttpClient(self.dest, redirect_mode=RedirectMode.SAME_ORIGIN)
        with patch.object(client._session, "request", side_effect=[_redirect(302, "http://example.com/x")]) as mock_req:
            resp = client.request("GET", "/path")
        assert resp.status_code == 302
        assert mock_req.call_count == 1

    def test_same_origin_rejects_userinfo_in_location(self):
        client = DestinationHttpClient(self.dest, redirect_mode=RedirectMode.SAME_ORIGIN)
        with patch.object(client._session, "request", side_effect=[_redirect(302, "https://user:pass@example.com/x")]) as mock_req:
            resp = client.request("GET", "/path")
        assert resp.status_code == 302
        assert mock_req.call_count == 1

    def test_303_converts_to_get_and_drops_body(self):
        client = DestinationHttpClient(self.dest, redirect_mode=RedirectMode.SAME_ORIGIN)
        with patch.object(client._session, "request", side_effect=[_redirect(303, "/result"), _ok()]) as mock_req:
            resp = client.request("POST", "/submit", json={"data": "v"})
        assert resp.status_code == 200
        second = mock_req.call_args_list[1].kwargs
        assert second["method"] == "GET"
        assert second["json"] is None

    def test_chain_stops_at_cross_origin_hop(self):
        """First two hops are same-origin; third is cross-origin — stops and returns third 302."""
        client = DestinationHttpClient(self.dest, redirect_mode=RedirectMode.SAME_ORIGIN)
        chain = [
            _redirect(302, "/hop1"),
            _redirect(302, "/hop2"),
            _redirect(302, "https://other.com/evil"),
        ]
        with patch.object(client._session, "request", side_effect=chain) as mock_req:
            resp = client.request("GET", "/start")
        assert resp.status_code == 302
        assert mock_req.call_count == 3  # third call returned the cross-origin redirect

    def test_max_hops_returns_last_redirect(self):
        """When the hop limit is exhausted, the last redirect response is returned."""
        from sap_cloud_sdk.destination._destination_http_client import _MAX_REDIRECT_HOPS
        client = DestinationHttpClient(self.dest, redirect_mode=RedirectMode.SAME_ORIGIN)
        # _MAX_REDIRECT_HOPS same-origin hops + one that never fires
        chain = [_redirect(302, f"/hop{i}") for i in range(_MAX_REDIRECT_HOPS + 1)]
        with patch.object(client._session, "request", side_effect=chain) as mock_req:
            resp = client.request("GET", "/start")
        assert resp.status_code == 302
        assert mock_req.call_count == _MAX_REDIRECT_HOPS
