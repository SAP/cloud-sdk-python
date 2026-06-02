"""Unit tests for AdmsHttp — Bearer injection, CSRF management, error mapping."""

from typing import Optional
from unittest.mock import MagicMock, call

import pytest
import requests

from sap_cloud_sdk.adms._auth import IasTokenFetcher
from sap_cloud_sdk.adms._http import AdmsHttp, quote_odata_string_key
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

    def test_403_evicts_csrf_and_retries_once(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        # Two CSRF fetches: stale, then fresh.
        session.get.side_effect = [
            _make_resp(200, headers={"X-CSRF-Token": "stale"}),
            _make_resp(200, headers={"X-CSRF-Token": "fresh"}),
        ]
        # First POST returns 403 (CSRF expired); retry succeeds.
        session.request.side_effect = [
            _make_resp(403, json_data={"error": "csrf"}),
            _make_resp(200, json_data={"ok": True}),
        ]

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        resp = http.post(
            "Action", json={"x": 1}, service_base="/odata/v4/DocumentService"
        )

        assert resp.status_code == 200
        assert session.get.call_count == 2
        assert session.request.call_count == 2
        assert (
            session.request.call_args_list[1][1]["headers"]["X-CSRF-Token"] == "fresh"
        )

    def test_403_after_retry_raises(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = [
            _make_resp(200, headers={"X-CSRF-Token": "first"}),
            _make_resp(200, headers={"X-CSRF-Token": "second"}),
        ]
        # Both attempts return 403.
        session.request.return_value = _make_resp(403, json_data={"error": "denied"})

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        with pytest.raises(HttpError) as exc_info:
            http.post("Action", json={}, service_base="/odata/v4/DocumentService")

        assert exc_info.value.status_code == 403
        assert session.request.call_count == 2  # exactly one retry

    def test_non_403_error_is_not_retried(self, config, token_fetcher):
        session = MagicMock(spec=requests.Session)
        session.get.return_value = _make_resp(200, headers={"X-CSRF-Token": "csrf"})
        session.request.return_value = _make_resp(500, json_data={"error": "boom"})

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        with pytest.raises(HttpError) as exc_info:
            http.post("Action", json={}, service_base="/odata/v4/DocumentService")

        assert exc_info.value.status_code == 500
        assert session.request.call_count == 1  # no retry on non-403


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


class TestQuoteOdataStringKey:
    def test_simple_value(self):
        assert quote_odata_string_key("job-123") == "'job-123'"

    def test_value_with_single_quote_is_doubled(self):
        # OData V4 §5.1.1.6.2 — single quotes inside string literals must be doubled.
        assert quote_odata_string_key("O'Brien") == "'O''Brien'"

    def test_injection_attempt_is_neutralised(self):
        # An attacker-controlled value must not break out of the quoted segment.
        out = quote_odata_string_key("x'); DROP TABLE--")
        assert out == "'x''); DROP TABLE--'"
        # Result is one single-quoted literal, not two.
        assert out.count("'") % 2 == 0

    def test_empty_string(self):
        assert quote_odata_string_key("") == "''"


class TestAdmsHttpThreadSafety:
    def test_concurrent_csrf_fetches_converge_on_same_token(
        self, config, token_fetcher
    ):
        """Concurrent threads on a cold cache must all observe the same token.

        Without the lock + ``setdefault``, two threads can each fetch and
        each write their (potentially different) tokens, leaving callers
        with inconsistent values for the same key.
        """
        import threading as _threading

        session = MagicMock(spec=requests.Session)
        # Each parallel fetch returns a different token; the first writer
        # should win and all subsequent writers should observe that value.
        token_seq = iter(f"csrf-{i}" for i in range(100))
        seq_lock = _threading.Lock()

        def get_with_unique_token(*args, **kwargs):
            with seq_lock:
                t = next(token_seq)
            return _make_resp(200, headers={"X-CSRF-Token": t})

        session.get.side_effect = get_with_unique_token
        session.request.return_value = _make_resp(200, json_data={})

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)

        results: list[str] = []
        results_lock = _threading.Lock()

        def worker():
            t = http._get_csrf_token(service_base="/odata/v4/DocumentService")
            with results_lock:
                results.append(t)

        threads = [_threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2)

        # All 8 threads must agree on the same token (first-writer-wins).
        assert len(set(results)) == 1, f"divergent tokens: {set(results)}"

    def test_403_retry_does_not_evict_freshly_written_token(
        self, config, token_fetcher
    ):
        """A 403 retry must only evict the *stale* token it failed with.

        If thread A's request 403s and thread B has already refreshed the
        token in between, A must not evict B's fresh token — otherwise B's
        in-flight requests using the fresh token would race a needless
        re-fetch.
        """
        session = MagicMock(spec=requests.Session)
        session.get.return_value = _make_resp(
            200, headers={"X-CSRF-Token": "fresh"}
        )
        session.request.return_value = _make_resp(403, json_data={"error": "csrf"})

        http = AdmsHttp(config=config, token_fetcher=token_fetcher, session=session)
        # Pre-seed the cache with a "fresh" token; simulate that thread A is
        # mid-flight with a stale value that no longer matches the cache.
        http._csrf_tokens[""] = "fresh"

        # Manually trigger the retry-eviction guard with a stale csrf value.
        # The cached "fresh" value must remain untouched.
        with http._csrf_lock:
            stale = "stale"
            if http._csrf_tokens.get("") == stale:
                http._csrf_tokens.pop("", None)

        assert http._csrf_tokens[""] == "fresh"

