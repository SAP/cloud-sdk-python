"""Unit tests for the service-backed thread registry."""

from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.agent_memory.config import AgentMemoryConfig
from sap_cloud_sdk.core.protocol.http import HttpClient, HttpMethod
from sap_cloud_sdk.core.runtime_context._context import sdk_context
from sap_cloud_sdk.core.runtime_context import RuntimeContext
from sap_cloud_sdk.core.runtime_context.providers._ias import IAS_TOKEN
from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryHttpError,
    AgentMemoryNotFoundError,
    AgentMemoryThreadConflictError,
    AgentMemoryThreadExpiredError,
    AgentMemoryThreadNotFoundError,
    AgentMemoryValidationError,
)
from sap_cloud_sdk.agent_memory.thread_registry import SAPAgentMemoryThreadRegistry
from sap_cloud_sdk.agent_memory.thread_registry._service import (
    _build_list_path,
    _escape_odata_string,
    _is_expired_response,
    _odata_entity_path,
)
from sap_cloud_sdk.core.telemetry import Module, Operation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = "https://agent-memory.example.com"


def _make_registry(base_url=_BASE, default_ttl=None):
    reg = SAPAgentMemoryThreadRegistry.__new__(SAPAgentMemoryThreadRegistry)
    reg._http = MagicMock(spec=HttpClient)
    reg._request = MagicMock()
    reg._base_url = base_url.rstrip("/")
    reg._default_ttl = default_ttl
    return reg


_ENTRY = {
    "threadId": "t-1",
    "agentId": "agent-a",
    "invokerId": "user-1",
    "description": None,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
    "expiresAt": None,
    "threadTtl": None,
    "metadata": None,
}


# ---------------------------------------------------------------------------
# OData URL helpers
# ---------------------------------------------------------------------------


class TestODataHelpers:
    def test_escape_odata_string_no_quotes(self):
        assert _escape_odata_string("hello") == "hello"

    def test_escape_odata_string_single_quotes_doubled(self):
        assert _escape_odata_string("it's") == "it''s"

    def test_escape_odata_string_multiple_quotes(self):
        assert _escape_odata_string("a'b'c") == "a''b''c"

    def test_odata_entity_path_basic(self):
        path = _odata_entity_path("t-1")
        assert path == "/v1/agent/threads(threadId='t-1')"

    def test_odata_entity_path_escapes_single_quote(self):
        path = _odata_entity_path("t'1")
        # Single quotes are doubled (OData) then percent-encoded (%27%27).
        assert "%27%27" in path

    def test_build_list_path_includes_orderby(self):
        path = _build_list_path(None, None, None, 0)
        assert "$orderby=" in path
        assert "$count=true" in path

    def test_build_list_path_adds_top(self):
        path = _build_list_path(None, None, 10, 0)
        assert "$top=10" in path

    def test_build_list_path_adds_skip(self):
        path = _build_list_path(None, None, None, 5)
        assert "$skip=5" in path

    def test_build_list_path_omits_skip_when_zero(self):
        path = _build_list_path(None, None, None, 0)
        assert "$skip" not in path

    def test_build_list_path_filter_agent_id(self):
        path = _build_list_path("my-agent", None, None, 0)
        assert "agentId" in path
        assert "my-agent" in path

    def test_build_list_path_filter_invoker_id(self):
        path = _build_list_path(None, "user-1", None, 0)
        assert "invokerId" in path
        assert "user-1" in path

    def test_build_list_path_no_dollar_sign_encoding(self):
        path = _build_list_path(None, None, None, 0)
        assert "%24" not in path  # $ must not be percent-encoded


# ---------------------------------------------------------------------------
# _is_expired_response (issue 3: structured 409 detection)
# ---------------------------------------------------------------------------


class TestIsExpiredResponse:
    def _exc(self, msg: str = "", response_text: str = "") -> AgentMemoryHttpError:
        return AgentMemoryHttpError(msg, status_code=409, response_text=response_text)

    def test_plain_text_expired_in_response_body(self):
        assert (
            _is_expired_response(self._exc(response_text="Thread has expired")) is True
        )

    def test_plain_text_conflict_returns_false(self):
        assert (
            _is_expired_response(self._exc(response_text="Thread already owned"))
            is False
        )

    def test_expired_in_exception_message_not_body_returns_false(self):
        # The fallback searches only the response body, never the exception
        # message — an unrelated 409 whose prose mentions "expired" (e.g. an
        # OAuth-token error) must not be misclassified as a thread expiry.
        assert _is_expired_response(self._exc(msg="expired thread")) is False

    def test_json_error_code_expired(self):
        import json

        body = json.dumps({"error": {"code": "THREAD_EXPIRED", "message": "gone"}})
        assert _is_expired_response(self._exc(response_text=body)) is True

    def test_json_error_code_conflict_returns_false(self):
        import json

        body = json.dumps(
            {"error": {"code": "OWNERSHIP_CONFLICT", "message": "conflict"}}
        )
        assert _is_expired_response(self._exc(response_text=body)) is False

    def test_json_top_level_errorCode_expired(self):
        import json

        body = json.dumps({"errorCode": "expired", "message": "gone"})
        assert _is_expired_response(self._exc(response_text=body)) is True

    def test_json_code_takes_priority_over_body_text(self):
        import json

        # Structured code says CONFLICT even though the message text says "expired" —
        # the code field must win.
        body = json.dumps({"error": {"code": "CONFLICT"}, "message": "thread expired"})
        assert _is_expired_response(self._exc(response_text=body)) is False

    def test_malformed_json_falls_back_to_string_match(self):
        assert _is_expired_response(self._exc(response_text='{"bad json')) is False

    def test_empty_response_text_and_non_expired_message(self):
        assert (
            _is_expired_response(self._exc(msg="some conflict", response_text=""))
            is False
        )


# ---------------------------------------------------------------------------
# Transport lifecycle
# ---------------------------------------------------------------------------


class TestTransportLifecycle:
    def test_close_delegates_to_transport(self):
        reg = _make_registry()
        reg.close()
        reg._http.close.assert_called_once()

    def test_context_manager_returns_self(self):
        reg = _make_registry()
        with reg as r:
            assert r is reg

    def test_context_manager_closes_on_exit(self):
        reg = _make_registry()
        with reg:
            pass
        reg._http.close.assert_called_once()

    def test_context_manager_closes_even_on_exception(self):
        reg = _make_registry()
        with pytest.raises(RuntimeError):
            with reg:
                raise RuntimeError("boom")
        reg._http.close.assert_called_once()


# ---------------------------------------------------------------------------
# create_or_register_thread
# ---------------------------------------------------------------------------


class TestCreateOrRegisterThread:
    def test_server_assigned_id_posts_body(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()

        reg.create_or_register_thread("agent-a", "user-1")

        reg._request.assert_called_once()
        call_args = reg._request.call_args
        assert call_args[0][0] == HttpMethod.POST
        assert call_args[0][1] == "/v1/agent/threads"
        body = call_args[1]["json"]
        assert body["agentId"] == "agent-a"
        assert body["invokerId"] == "user-1"
        assert "threadId" not in body

    def test_returns_parsed_entry(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        e = reg.create_or_register_thread("agent-a", "user-1")
        assert e["threadId"] == "t-1"
        assert e["agentId"] == "agent-a"

    def test_with_explicit_thread_id_included_in_body(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        body = reg._request.call_args[1]["json"]
        assert body["threadId"] == "t-1"

    def test_description_included_when_provided(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        reg.create_or_register_thread("agent-a", "user-1", description="my desc")
        body = reg._request.call_args[1]["json"]
        assert body["description"] == "my desc"

    def test_metadata_included_when_provided(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        reg.create_or_register_thread("agent-a", "user-1", metadata={"x": 1})
        body = reg._request.call_args[1]["json"]
        assert body["metadata"] == {"x": 1}

    def test_idle_ttl_sent_as_threadTtl(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        reg.create_or_register_thread("agent-a", "user-1", ttl_seconds=3600)
        body = reg._request.call_args[1]["json"]
        assert body["threadTtl"] == 3600

    def test_default_ttl_used_when_no_per_call_ttl(self):
        reg = _make_registry(default_ttl=1800)
        reg._request.return_value = _ENTRY.copy()
        reg.create_or_register_thread("agent-a", "user-1")
        body = reg._request.call_args[1]["json"]
        assert body["threadTtl"] == 1800

    def test_per_call_ttl_overrides_default(self):
        reg = _make_registry(default_ttl=1800)
        reg._request.return_value = _ENTRY.copy()
        reg.create_or_register_thread("agent-a", "user-1", ttl_seconds=300)
        body = reg._request.call_args[1]["json"]
        assert body["threadTtl"] == 300

    def test_tenant_id_forwarded(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        reg.create_or_register_thread("agent-a", "user-1", tenant_subdomain="acme")
        assert reg._request.call_args[1]["tenant_subdomain"] == "acme"

    def test_no_tenant_id_passes_none(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        reg.create_or_register_thread("agent-a", "user-1")
        assert reg._request.call_args[1]["tenant_subdomain"] is None

    def test_409_without_expired_raises_conflict_when_thread_id_given(self):
        reg = _make_registry()
        reg._request.side_effect = AgentMemoryHttpError(
            "conflict", status_code=409, response_text="Thread already owned"
        )
        with pytest.raises(AgentMemoryThreadConflictError):
            reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")

    def test_409_with_expired_raises_thread_expired(self):
        reg = _make_registry()
        reg._request.side_effect = AgentMemoryHttpError(
            "expired", status_code=409, response_text="Thread has expired"
        )
        with pytest.raises(AgentMemoryThreadExpiredError):
            reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")

    def test_409_expired_detected_from_json_error_code(self):
        import json

        reg = _make_registry()
        reg._request.side_effect = AgentMemoryHttpError(
            "conflict",
            status_code=409,
            response_text=json.dumps(
                {"error": {"code": "THREAD_EXPIRED", "message": "gone"}}
            ),
        )
        with pytest.raises(AgentMemoryThreadExpiredError):
            reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")

    def test_409_without_thread_id_re_raised_as_http_error(self):
        reg = _make_registry()
        reg._request.side_effect = AgentMemoryHttpError(
            "conflict", status_code=409, response_text="conflict"
        )
        with pytest.raises(AgentMemoryHttpError):
            reg.create_or_register_thread("agent-a", "user-1")

    def test_invalid_ttl_raises_value_error(self):
        reg = _make_registry()
        with pytest.raises(ValueError, match="ttl_seconds"):
            reg.create_or_register_thread("agent-a", "user-1", ttl_seconds=-1)

    def test_boolean_ttl_raises_value_error(self):
        reg = _make_registry()
        with pytest.raises(ValueError, match="ttl_seconds"):
            reg.create_or_register_thread("agent-a", "user-1", ttl_seconds=True)


# ---------------------------------------------------------------------------
# get_thread
# ---------------------------------------------------------------------------


class TestGetThread:
    def test_uses_odata_entity_path(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        reg.get_thread("t-1")
        call_args = reg._request.call_args
        assert call_args[0][0] == HttpMethod.GET
        path = call_args[0][1]
        assert "t-1" in path
        assert path.startswith("/v1/agent/threads(")

    def test_returns_parsed_entry(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        e = reg.get_thread("t-1")
        assert e["threadId"] == "t-1"

    def test_not_found_raises_thread_not_found(self):
        reg = _make_registry()
        reg._request.side_effect = AgentMemoryNotFoundError("not found")
        with pytest.raises(AgentMemoryThreadNotFoundError, match="t-1"):
            reg.get_thread("t-1")

    def test_tenant_id_forwarded(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        reg.get_thread("t-1", tenant_subdomain="acme")
        assert reg._request.call_args[1]["tenant_subdomain"] == "acme"


# ---------------------------------------------------------------------------
# list_threads
# ---------------------------------------------------------------------------


class TestListThreads:
    def _page_response(self, entries, total=None, next_link=None):
        body: dict = {"value": entries, "@odata.count": total or len(entries)}
        if next_link:
            body["@odata.nextLink"] = next_link
        return body

    def test_returns_thread_page(self):
        reg = _make_registry()
        reg._request.return_value = self._page_response([_ENTRY.copy()])
        page = reg.list_threads()
        assert len(page["entries"]) == 1
        assert page["total"] == 1

    def test_with_limit_uses_top(self):
        reg = _make_registry()
        reg._request.return_value = self._page_response([_ENTRY.copy()])
        reg.list_threads(limit=5)
        path = reg._request.call_args[0][1]
        assert "$top=5" in path

    def test_with_offset_uses_skip(self):
        reg = _make_registry()
        reg._request.return_value = self._page_response([])
        reg.list_threads(limit=5, offset=10)
        path = reg._request.call_args[0][1]
        assert "$skip=10" in path

    def test_limit_zero_calls_transport_for_count(self):
        reg = _make_registry()
        reg._request.return_value = self._page_response([], total=7)
        page = reg.list_threads(limit=0)
        path = reg._request.call_args[0][1]
        assert "$top=0" in path
        assert "$count=true" in path
        assert page["entries"] == []
        assert page["total"] == 7

    def test_follows_next_link(self):
        reg = _make_registry()
        next_link = f"{_BASE}/v1/agent/threads?$top=1&$skip=1"
        first_page = self._page_response([_ENTRY.copy()], total=2, next_link=next_link)
        second_page = self._page_response([{**_ENTRY, "threadId": "t-2"}], total=2)
        reg._request.side_effect = [first_page, second_page]

        page = reg.list_threads()  # no limit = follow all pages

        assert len(page["entries"]) == 2
        assert reg._request.call_count == 2

    def test_next_link_strips_base_url(self):
        reg = _make_registry()
        next_link = f"{_BASE}/v1/agent/threads?$skip=1"
        first = self._page_response([_ENTRY.copy()], total=2, next_link=next_link)
        second = self._page_response([{**_ENTRY, "threadId": "t-2"}], total=2)
        reg._request.side_effect = [first, second]
        reg.list_threads()
        second_call_path = reg._request.call_args_list[1][0][1]
        assert not second_call_path.startswith("http")
        assert second_call_path.startswith("/")

    def test_filter_agent_id_in_path(self):
        reg = _make_registry()
        reg._request.return_value = self._page_response([])
        reg.list_threads(agent_id="my-agent")
        path = reg._request.call_args[0][1]
        assert "my-agent" in path

    def test_filter_invoker_id_in_path(self):
        reg = _make_registry()
        reg._request.return_value = self._page_response([])
        reg.list_threads(invoker_id="user-1")
        path = reg._request.call_args[0][1]
        assert "user-1" in path

    def test_invalid_limit_raises_value_error(self):
        reg = _make_registry()
        with pytest.raises(ValueError, match="limit"):
            reg.list_threads(limit=-1)

    def test_boolean_limit_raises_value_error(self):
        """Finding 8: limit=False must not bypass the limit==0 early-return via False==0."""
        reg = _make_registry()
        with pytest.raises(ValueError, match="limit"):
            reg.list_threads(limit=False)

    def test_boolean_true_limit_raises_value_error(self):
        """Finding 8: limit=True (== 1 numerically) should also raise, not silently fetch 1 item."""
        reg = _make_registry()
        with pytest.raises(ValueError, match="limit"):
            reg.list_threads(limit=True)

    def test_invalid_offset_raises_value_error(self):
        reg = _make_registry()
        with pytest.raises(ValueError, match="offset"):
            reg.list_threads(offset=-1)

    def test_tenant_id_forwarded(self):
        reg = _make_registry()
        reg._request.return_value = self._page_response([])
        reg.list_threads(tenant_subdomain="acme")
        assert reg._request.call_args[1]["tenant_subdomain"] == "acme"


# ---------------------------------------------------------------------------
# update_thread
# ---------------------------------------------------------------------------


class TestUpdateThread:
    def test_patches_entity_path_then_gets(self):
        reg = _make_registry()
        reg._request.side_effect = [{}, _ENTRY.copy()]

        reg.update_thread("t-1", description="new desc")

        assert reg._request.call_count == 2
        patch_call = reg._request.call_args_list[0]
        assert patch_call[0][0] == HttpMethod.PATCH
        patch_path = patch_call[0][1]
        assert "t-1" in patch_path
        assert patch_path.startswith("/v1/agent/threads(")

        get_call = reg._request.call_args_list[1]
        assert get_call[0][0] == HttpMethod.GET

    def test_body_excludes_thread_id(self):
        reg = _make_registry()
        reg._request.side_effect = [{}, _ENTRY.copy()]
        reg.update_thread("t-1")
        body = reg._request.call_args_list[0][1]["json"]
        assert "threadId" not in body

    def test_description_included_in_body(self):
        reg = _make_registry()
        reg._request.side_effect = [{}, _ENTRY.copy()]
        reg.update_thread("t-1", description="new")
        body = reg._request.call_args_list[0][1]["json"]
        assert body["description"] == "new"

    def test_idle_ttl_sent_as_threadTtl(self):
        reg = _make_registry()
        reg._request.side_effect = [{}, _ENTRY.copy()]
        reg.update_thread("t-1", ttl_seconds=600)
        body = reg._request.call_args_list[0][1]["json"]
        assert body["threadTtl"] == 600

    def test_ttl_none_omits_threadTtl_leaving_it_unchanged(self):
        reg = _make_registry()
        reg._request.side_effect = [{}, _ENTRY.copy()]
        reg.update_thread("t-1", description="x")
        body = reg._request.call_args_list[0][1]["json"]
        assert "threadTtl" not in body

    def test_default_ttl_not_reapplied_on_update(self):
        # A description-only update must not resend the registry default TTL,
        # otherwise it would silently reset a per-thread TTL override.
        reg = _make_registry(default_ttl=7200)
        reg._request.side_effect = [{}, _ENTRY.copy()]
        reg.update_thread("t-1", description="x")
        body = reg._request.call_args_list[0][1]["json"]
        assert "threadTtl" not in body

    def test_not_found_raises_thread_not_found(self):
        reg = _make_registry()
        reg._request.side_effect = AgentMemoryNotFoundError("not found")
        with pytest.raises(AgentMemoryThreadNotFoundError, match="t-1"):
            reg.update_thread("t-1", description="x")

    def test_returns_refreshed_entry(self):
        reg = _make_registry()
        refreshed = {**_ENTRY, "description": "updated"}
        reg._request.side_effect = [{}, refreshed]
        e = reg.update_thread("t-1", description="updated")
        assert e["description"] == "updated"

    def test_tenant_id_forwarded_to_both_calls(self):
        reg = _make_registry()
        reg._request.side_effect = [{}, _ENTRY.copy()]
        reg.update_thread("t-1", tenant_subdomain="acme")
        assert reg._request.call_args_list[0][1]["tenant_subdomain"] == "acme"
        assert reg._request.call_args_list[1][1]["tenant_subdomain"] == "acme"

    def test_invalid_ttl_raises_value_error(self):
        reg = _make_registry()
        with pytest.raises(ValueError, match="ttl_seconds"):
            reg.update_thread("t-1", ttl_seconds=0)


# ---------------------------------------------------------------------------
# delete_thread
# ---------------------------------------------------------------------------


class TestDeleteThread:
    def test_calls_delete_with_entity_path(self):
        reg = _make_registry()
        reg._request.return_value = {}
        reg.delete_thread("t-1")
        call_args = reg._request.call_args
        assert call_args[0][0] == HttpMethod.DELETE
        path = call_args[0][1]
        assert "t-1" in path
        assert path.startswith("/v1/agent/threads(")

    def test_idempotent_swallows_not_found(self):
        reg = _make_registry()
        reg._request.side_effect = AgentMemoryNotFoundError("not found")
        reg.delete_thread("t-1")  # must not raise

    def test_tenant_id_forwarded(self):
        reg = _make_registry()
        reg._request.return_value = {}
        reg.delete_thread("t-1", tenant_subdomain="acme")
        assert reg._request.call_args[1]["tenant_subdomain"] == "acme"

    def test_other_http_errors_propagate(self):
        reg = _make_registry()
        reg._request.side_effect = AgentMemoryHttpError("server error", status_code=500)
        with pytest.raises(AgentMemoryHttpError):
            reg.delete_thread("t-1")


# ---------------------------------------------------------------------------
# End-to-end IAS flow
# ---------------------------------------------------------------------------


class TestIASEndToEnd:
    """Full chain: IAS ContextVar set → registry method → Bearer token on wire.

    Uses a real SAPAgentMemoryThreadRegistry (no mock _request) with a patched
    requests.Session so the HTTP call is intercepted at the network boundary.
    """

    def _make_registry_with_real_transport(self):
        config = AgentMemoryConfig(
            base_url=_BASE
        )  # IAS-mode: URL only, no OAuth2 creds
        return SAPAgentMemoryThreadRegistry(config)

    def test_create_thread_sends_ias_bearer_token(self):
        """create_or_register_thread() sends Authorization: Bearer <ias-token>."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.ok = True
        mock_response.content = b"{}"
        mock_response.json.return_value = {
            "threadId": "t-1",
            "agentId": "agent-a",
            "invokerId": "user-1",
        }

        with sdk_context(RuntimeContext({IAS_TOKEN: "ias-dummy-token-xyz"})):
            with patch(
                "sap_cloud_sdk.core.protocol.http.models.requests"
            ) as mock_requests:
                mock_session = MagicMock()
                mock_session.headers = {}
                mock_requests.Session.return_value = mock_session
                mock_session.request.return_value = mock_response

                reg = self._make_registry_with_real_transport()
                reg.create_or_register_thread(agent_id="agent-a", invoker_id="user-1")

        assert mock_session.headers["Authorization"] == "Bearer ias-dummy-token-xyz"

    def test_get_thread_sends_ias_bearer_token(self):
        """get_thread() passes the IAS token through HttpClient."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.content = b"{}"
        mock_response.json.return_value = {
            "threadId": "t-1",
            "agentId": "agent-a",
            "invokerId": "user-1",
        }

        with sdk_context(RuntimeContext({IAS_TOKEN: "ias-dummy-token-xyz"})):
            with patch(
                "sap_cloud_sdk.core.protocol.http.models.requests"
            ) as mock_requests:
                mock_session = MagicMock()
                mock_session.headers = {}
                mock_requests.Session.return_value = mock_session
                mock_session.request.return_value = mock_response

                reg = self._make_registry_with_real_transport()
                reg.get_thread("t-1")

        assert mock_session.headers["Authorization"] == "Bearer ias-dummy-token-xyz"

    def test_no_ias_token_raises_validation_error(self):
        """Without the IAS ContextVar, IAS-mode calls raise before any request.

        The missing-token guard runs in the client layer, so no HTTP request is
        ever dispatched when the token is absent.

        sdk_context(RuntimeContext({})) explicitly clears any ambient IAS token
        that a session-scoped integration fixture may have injected, making the
        test deterministic regardless of run order.
        """
        with patch("sap_cloud_sdk.core.protocol.http.models.requests") as mock_requests:
            mock_session = MagicMock()
            mock_requests.Session.return_value = mock_session

            reg = self._make_registry_with_real_transport()
            with sdk_context(RuntimeContext({})):
                with pytest.raises(
                    AgentMemoryValidationError, match="bootstrap\\(app\\)"
                ):
                    reg.get_thread("t-1")

        mock_session.request.assert_not_called()


# ---------------------------------------------------------------------------
# Telemetry metrics
# ---------------------------------------------------------------------------

_REQUEST_METRIC = "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
_ERROR_METRIC = "sap_cloud_sdk.core.telemetry.metrics_decorator.record_error_metric"


class TestTelemetry:
    """Each operation records a request metric on success and an error metric on failure.

    Operations are distinguished only by the Operation enum (the
    ``sap.cloud_sdk.functionality`` attribute); all share Module.AGENT_MEMORY.
    ``source`` is None here because the registry never sets ``_telemetry_source``.
    """

    def test_create_or_register_thread_records_request_metric(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        with patch(_REQUEST_METRIC) as metric:
            reg.create_or_register_thread("agent-a", "user-1")
        metric.assert_called_once_with(
            Module.AGENT_MEMORY,
            None,
            Operation.AGENT_MEMORY_CREATE_OR_REGISTER_THREAD,
            False,
        )

    def test_get_thread_records_request_metric(self):
        reg = _make_registry()
        reg._request.return_value = _ENTRY.copy()
        with patch(_REQUEST_METRIC) as metric:
            reg.get_thread("t-1")
        metric.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_GET_THREAD, False
        )

    def test_list_threads_records_request_metric(self):
        reg = _make_registry()
        reg._request.return_value = {"value": [], "@odata.count": 0}
        with patch(_REQUEST_METRIC) as metric:
            reg.list_threads(limit=10)
        metric.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_LIST_THREADS, False
        )

    def test_update_thread_records_single_request_metric(self):
        """update_thread must emit exactly one metric — the internal refreshing
        read goes through the undecorated _get_thread, so no stray get_thread."""
        reg = _make_registry()
        reg._request.side_effect = [{}, _ENTRY.copy()]
        with patch(_REQUEST_METRIC) as metric:
            reg.update_thread("t-1", description="new")
        metric.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_UPDATE_THREAD, False
        )

    def test_delete_thread_records_request_metric(self):
        reg = _make_registry()
        reg._request.return_value = {}
        with patch(_REQUEST_METRIC) as metric:
            reg.delete_thread("t-1")
        metric.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_DELETE_THREAD, False
        )

    def test_delete_thread_swallowed_404_counts_as_success(self):
        """An idempotent delete of a missing thread returns normally, so the
        request (not error) counter fires."""
        reg = _make_registry()
        reg._request.side_effect = AgentMemoryNotFoundError("not found")
        with patch(_REQUEST_METRIC) as req, patch(_ERROR_METRIC) as err:
            reg.delete_thread("t-1")
        req.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_DELETE_THREAD, False
        )
        err.assert_not_called()

    def test_get_thread_not_found_records_error_metric(self):
        reg = _make_registry()
        reg._request.side_effect = AgentMemoryNotFoundError("not found")
        with patch(_REQUEST_METRIC) as req, patch(_ERROR_METRIC) as err:
            with pytest.raises(AgentMemoryThreadNotFoundError):
                reg.get_thread("t-1")
        err.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_GET_THREAD, False
        )
        req.assert_not_called()

    def test_create_validation_error_records_error_metric(self):
        reg = _make_registry()
        with patch(_REQUEST_METRIC) as req, patch(_ERROR_METRIC) as err:
            with pytest.raises(ValueError):
                reg.create_or_register_thread("agent-a", "user-1", ttl_seconds=-1)
        err.assert_called_once_with(
            Module.AGENT_MEMORY,
            None,
            Operation.AGENT_MEMORY_CREATE_OR_REGISTER_THREAD,
            False,
        )
        req.assert_not_called()
