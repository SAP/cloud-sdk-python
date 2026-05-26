"""Unit tests for AdmsHttp — Bearer injection, CSRF management, error mapping."""

from typing import Optional
from unittest.mock import MagicMock, call

import pytest
import requests

from sap_cloud_sdk.adms._auth import IasTokenFetcher
from sap_cloud_sdk.adms._http import AdmsHttp
from sap_cloud_sdk.adms.config import AdmsConfig
from sap_cloud_sdk.adms.exceptions import DocumentNotFoundError, HttpError


@pytest.fixture
def config() -> AdmsConfig:
    return AdmsConfig(
        service_url="https://adm.example.com",
        ias_url="https://ias.example.com",
        client_id="client-id",
        client_secret="client-secret",
    )


@pytest.fixture
def token_fetcher(config):
    fetcher = MagicMock(spec=IasTokenFetcher)
    fetcher.get_token.return_value = "service-token"
    fetcher.exchange_token.return_value = "user-token"
    return fetcher


def _make_resp(status_code: int = 200, json_data: Optional[dict] = None, headers: Optional[dict] = None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.json.return_value = json_data or {}
    resp.text = str(json_data)
    resp.headers = headers or {}
    return resp


class TestAdmsHttpGet:
    def test_get_injects_bearer_token(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        session.get.return_value = _make_resp(200)
        session.request.return_value = _make_resp(200)

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        http.get("Document", service_base="/odata/v4/DocumentService")

        req_call = session.request.call_args
        headers = req_call[1]["headers"]
        assert headers["Authorization"] == "Bearer service-token"

    def test_get_uses_correct_url(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        session.request.return_value = _make_resp(200)
        # CSRF fetch
        session.get.return_value = _make_resp(200, headers={})

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        http.get("Document(ID='x')", service_base="/odata/v4/DocumentService")

        url = session.request.call_args[1]["url"]
        assert url == "https://adm.example.com/odata/v4/DocumentService/Document(ID='x')"

    def test_404_raises_document_not_found(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        session.request.return_value = _make_resp(404)

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        with pytest.raises(DocumentNotFoundError):
            http.get("Document(ID='missing')")

    def test_500_raises_http_error(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        session.request.return_value = _make_resp(500, json_data={"error": "oops"})

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        with pytest.raises(HttpError) as exc_info:
            http.get("Document")
        assert exc_info.value.status_code == 500

    def test_request_exception_raises_http_error(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        session.request.side_effect = requests.ConnectionError("no network")

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        with pytest.raises(HttpError, match="DMS request failed"):
            http.get("Document")


class TestAdmsHttpPost:
    def test_post_fetches_csrf_first(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        # CSRF fetch call
        csrf_resp = _make_resp(200, headers={"X-CSRF-Token": "csrf-abc"})
        session.get.return_value = csrf_resp
        # Actual POST
        session.request.return_value = _make_resp(200, json_data={"result": "ok"})

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        http.post("CreateDocumentWithRelation", json={"data": 1},
                  service_base="/odata/v4/DocumentService")

        req_headers = session.request.call_args[1]["headers"]
        assert req_headers["X-CSRF-Token"] == "csrf-abc"

    def test_csrf_token_is_cached_between_posts(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        csrf_resp = _make_resp(200, headers={"X-CSRF-Token": "csrf-xyz"})
        session.get.return_value = csrf_resp
        session.request.return_value = _make_resp(200, json_data={})

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        http.post("Action1", json={}, service_base="/odata/v4/DocumentService")
        http.post("Action2", json={}, service_base="/odata/v4/DocumentService")

        # CSRF fetch should only happen once
        assert session.get.call_count == 1


class TestAdmsHttpUserJwt:
    def test_user_jwt_uses_exchange_token(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        session.request.return_value = _make_resp(200)
        session.get.return_value = _make_resp(200, headers={})

        http = AdmsHttp(
            config=config,
            token_fetcher=token_fetcher,
            session=session,
            user_jwt="user-jwt-123",
        )
        http.get("Document")

        token_fetcher.exchange_token.assert_called_once_with("user-jwt-123")
        token_fetcher.get_token.assert_not_called()

    def test_service_jwt_uses_get_token(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        session.request.return_value = _make_resp(200)

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        http.get("Document")

        token_fetcher.get_token.assert_called()
        token_fetcher.exchange_token.assert_not_called()
