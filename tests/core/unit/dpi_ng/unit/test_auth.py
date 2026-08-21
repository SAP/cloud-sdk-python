from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from sap_cloud_sdk.core.dpi_ng.auth import (
    BearerTokenAuth,
    ClientCertificateAuth,
    ClientCredentialsAuth,
    _OAuth2Flow,
)


def _mock_session() -> MagicMock:
    session = MagicMock(spec=requests.Session)
    session.headers = {}
    return session


def _mock_post_response(access_token: str = "tok", expires_in: int = 3600) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"access_token": access_token, "expires_in": expires_in}
    resp.raise_for_status.return_value = None
    resp.status_code = 200
    return resp


class TestBearerTokenAuth:
    def test_empty_token_raises(self):
        with pytest.raises(ValueError, match="token must not be empty"):
            BearerTokenAuth("")

    def test_apply_sets_authorization_header(self):
        auth = BearerTokenAuth("my-token")
        session = _mock_session()
        auth.apply(session)
        assert session.headers["Authorization"] == "Bearer my-token"


class TestClientCredentialsAuth:
    def test_empty_token_url_raises(self):
        with pytest.raises(
            ValueError, match="token_url, client_id, and client_secret are all required"
        ):
            ClientCredentialsAuth("", "cid", "secret")

    def test_empty_client_id_raises(self):
        with pytest.raises(
            ValueError, match="token_url, client_id, and client_secret are all required"
        ):
            ClientCredentialsAuth("https://token.url", "", "secret")

    def test_empty_client_secret_raises(self):
        with pytest.raises(
            ValueError, match="token_url, client_id, and client_secret are all required"
        ):
            ClientCredentialsAuth("https://token.url", "cid", "")

    def test_apply_sets_session_auth_to_oauth2_flow(self):
        auth = ClientCredentialsAuth("https://token.url", "cid", "secret")
        session = _mock_session()
        auth.apply(session)
        assert isinstance(session.auth, _OAuth2Flow)


class TestClientCertificateAuth:
    def test_empty_cert_file_raises(self):
        with pytest.raises(ValueError, match="cert_file and key_file are required"):
            ClientCertificateAuth("", "key.pem")

    def test_empty_key_file_raises(self):
        with pytest.raises(ValueError, match="cert_file and key_file are required"):
            ClientCertificateAuth("cert.pem", "")

    def test_apply_sets_session_cert(self):
        auth = ClientCertificateAuth("cert.pem", "key.pem")
        session = _mock_session()
        auth.apply(session)
        assert session.cert == ("cert.pem", "key.pem")

    def test_apply_with_ca_file_sets_session_verify(self):
        auth = ClientCertificateAuth("cert.pem", "key.pem", ca_file="ca.pem")
        session = _mock_session()
        auth.apply(session)
        assert session.verify == "ca.pem"

    def test_apply_without_ca_file_does_not_set_session_verify(self):
        auth = ClientCertificateAuth("cert.pem", "key.pem")
        session = _mock_session()
        auth.apply(session)
        assigned_attrs = [str(c) for c in session.mock_calls]
        assert not any("verify" in call for call in assigned_attrs)


class TestOAuth2Flow:
    def test_first_call_fetches_token(self):
        flow = _OAuth2Flow("https://token.url", "cid", "secret")
        req = MagicMock()
        req.headers = {}
        with patch(
            "sap_cloud_sdk.core.dpi_ng.auth.requests.post",
            return_value=_mock_post_response(),
        ) as mock_post:
            flow(req)
            mock_post.assert_called_once()

    def test_call_injects_bearer_header(self):
        flow = _OAuth2Flow("https://token.url", "cid", "secret")
        req = MagicMock()
        req.headers = {}
        with patch(
            "sap_cloud_sdk.core.dpi_ng.auth.requests.post",
            return_value=_mock_post_response("my-access-token"),
        ):
            result = flow(req)
        assert result.headers["Authorization"] == "Bearer my-access-token"  # ty: ignore[not-subscriptable]

    def test_second_call_reuses_cached_token(self):
        flow = _OAuth2Flow("https://token.url", "cid", "secret")
        req1 = MagicMock()
        req1.headers = {}
        req2 = MagicMock()
        req2.headers = {}
        with patch(
            "sap_cloud_sdk.core.dpi_ng.auth.requests.post",
            return_value=_mock_post_response(),
        ) as mock_post:
            flow(req1)
            flow(req2)
            mock_post.assert_called_once()

    def test_expired_token_triggers_refresh(self):
        flow = _OAuth2Flow("https://token.url", "cid", "secret")
        flow._access_token = "old-token"
        flow._expires_at = 0.0
        req = MagicMock()
        req.headers = {}
        with patch(
            "sap_cloud_sdk.core.dpi_ng.auth.requests.post",
            return_value=_mock_post_response("new-token"),
        ) as mock_post:
            flow(req)
            mock_post.assert_called_once()
        assert req.headers["Authorization"] == "Bearer new-token"

    def test_fetch_token_raises_on_non_200(self):
        flow = _OAuth2Flow("https://token.url", "cid", "secret")
        error_resp = MagicMock()
        error_resp.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        error_resp.status_code = 401
        req = MagicMock()
        req.headers = {}
        with patch(
            "sap_cloud_sdk.core.dpi_ng.auth.requests.post",
            return_value=error_resp,
        ):
            with pytest.raises(requests.HTTPError):
                flow(req)
