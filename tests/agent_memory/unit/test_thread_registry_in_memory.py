"""Unit tests for InMemoryThreadRegistry."""

import time
from unittest.mock import patch

import pytest

from sap_cloud_sdk.agent_memory.exceptions import (
    AgentMemoryThreadConflictError,
    AgentMemoryThreadExpiredError,
    AgentMemoryThreadNotFoundError,
)
from sap_cloud_sdk.agent_memory.thread_registry import InMemoryThreadRegistry
from sap_cloud_sdk.core.telemetry import Module, Operation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reg():
    return InMemoryThreadRegistry()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


class TestInMemoryThreadRegistryCRUD:
    def test_create_or_register_and_get(self, reg):
        e = reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        assert e["threadId"] == "t-1"
        assert e["agentId"] == "agent-a"
        assert e["invokerId"] == "user-1"

        got = reg.get_thread("t-1")
        assert got["threadId"] == "t-1"

    def test_get_missing_raises(self, reg):
        with pytest.raises(AgentMemoryThreadNotFoundError, match="t-missing"):
            reg.get_thread("t-missing")

    def test_idempotent_create_or_register_same_owner(self, reg):
        e1 = reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        e2 = reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        assert e1["threadId"] == e2["threadId"]

    def test_ownership_conflict(self, reg):
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        with pytest.raises(AgentMemoryThreadConflictError):
            reg.create_or_register_thread("agent-b", "user-2", thread_id="t-1")

    def test_create_without_thread_id_assigns_uuid(self, reg):
        e = reg.create_or_register_thread("agent-a", "user-1")
        assert len(e["threadId"]) == 36  # UUID format

    def test_list_threads(self, reg):
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        reg.create_or_register_thread("agent-b", "user-2", thread_id="t-2")
        page = reg.list_threads()
        assert len(page["entries"]) == 2
        assert page["total"] == 2

    def test_list_threads_filter_agent_id(self, reg):
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        reg.create_or_register_thread("agent-b", "user-2", thread_id="t-2")
        page = reg.list_threads(agent_id="agent-a")
        assert len(page["entries"]) == 1
        assert page["entries"][0]["threadId"] == "t-1"

    def test_list_threads_filter_invoker_id(self, reg):
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        reg.create_or_register_thread("agent-a", "user-2", thread_id="t-2")
        page = reg.list_threads(invoker_id="user-2")
        assert len(page["entries"]) == 1
        assert page["entries"][0]["threadId"] == "t-2"

    def test_list_threads_returns_thread_page_fields(self, reg):
        for i in range(5):
            reg.create_or_register_thread("agent-a", "user-1", thread_id=f"t-{i}")
        page = reg.list_threads(agent_id="agent-a", limit=3, offset=1)
        assert page["total"] == 5
        assert page["limit"] == 3
        assert page["offset"] == 1
        assert len(page["entries"]) == 3

    def test_list_threads_no_limit_returns_all(self):
        r = InMemoryThreadRegistry()
        for i in range(5):
            r.create_or_register_thread("agent-a", "user-1", thread_id=f"t-{i}")
        page = r.list_threads()
        assert page["limit"] == 5
        assert len(page["entries"]) == 5
        assert page["total"] == 5

    @pytest.mark.parametrize("bad_limit", [-1, -100, False, True, 1.5])
    def test_list_threads_invalid_limit_raises(self, bad_limit):
        r = InMemoryThreadRegistry()
        with pytest.raises(ValueError, match="limit"):
            r.list_threads(limit=bad_limit)

    @pytest.mark.parametrize("bad_offset", [-1, -100, False, True, 2.5])
    def test_list_threads_invalid_offset_raises(self, bad_offset):
        r = InMemoryThreadRegistry()
        with pytest.raises(ValueError, match="offset"):
            r.list_threads(offset=bad_offset)

    def test_list_threads_limit_zero_returns_empty(self):
        r = InMemoryThreadRegistry()
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        page = r.list_threads(limit=0)
        assert page["entries"] == []
        assert page["limit"] == 0

    def test_update_thread(self, reg):
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        updated = reg.update_thread("t-1", description="new desc", metadata={"k": "v"})
        assert updated["description"] == "new desc"
        assert updated["metadata"] == {"k": "v"}

    def test_update_missing_raises(self, reg):
        with pytest.raises(AgentMemoryThreadNotFoundError):
            reg.update_thread("t-missing", description="x")

    def test_delete_thread(self, reg):
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        reg.delete_thread("t-1")
        with pytest.raises(AgentMemoryThreadNotFoundError):
            reg.get_thread("t-1")

    def test_delete_idempotent(self, reg):
        reg.delete_thread("t-nonexistent")  # must not raise


# ---------------------------------------------------------------------------
# Sliding idle TTL
# ---------------------------------------------------------------------------


class TestInMemoryThreadRegistrySlidingTTL:
    def test_no_ttl_thread_never_expires(self):
        r = InMemoryThreadRegistry()
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        assert r.get_thread("t-1")["threadId"] == "t-1"

    def test_thread_expires_after_idle_ttl(self, monkeypatch):
        r = InMemoryThreadRegistry(default_ttl_seconds=10)
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        entry = r._store["t-1"]
        monkeypatch.setattr(entry, "last_active", time.monotonic() - 11)
        with pytest.raises(AgentMemoryThreadNotFoundError):
            r.get_thread("t-1")

    def test_list_omits_expired(self, monkeypatch):
        r = InMemoryThreadRegistry(default_ttl_seconds=10)
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-2")
        entry = r._store["t-1"]
        monkeypatch.setattr(entry, "last_active", time.monotonic() - 11)
        page = r.list_threads()
        assert len(page["entries"]) == 1
        assert page["entries"][0]["threadId"] == "t-2"

    def test_update_slides_window(self, monkeypatch):
        r = InMemoryThreadRegistry(default_ttl_seconds=10)
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        entry = r._store["t-1"]
        monkeypatch.setattr(entry, "last_active", time.monotonic() - 9)
        r.update_thread("t-1", description="touched")
        assert r.get_thread("t-1")["threadId"] == "t-1"

    def test_none_ttl_never_expires(self):
        r = InMemoryThreadRegistry(default_ttl_seconds=None)
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        assert r.get_thread("t-1")["threadId"] == "t-1"


# ---------------------------------------------------------------------------
# ThreadExpired on re-creation
# ---------------------------------------------------------------------------


class TestInMemoryThreadRegistryExpired:
    def test_create_or_register_expired_raises_thread_expired(self, monkeypatch):
        r = InMemoryThreadRegistry(default_ttl_seconds=10)
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        entry = r._store["t-1"]
        monkeypatch.setattr(entry, "last_active", time.monotonic() - 11)
        with pytest.raises(AgentMemoryThreadExpiredError, match="t-1"):
            r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")

    def test_expired_check_takes_priority_over_ownership(self, monkeypatch):
        r = InMemoryThreadRegistry(default_ttl_seconds=10)
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        entry = r._store["t-1"]
        monkeypatch.setattr(entry, "last_active", time.monotonic() - 11)
        with pytest.raises(AgentMemoryThreadExpiredError):
            r.create_or_register_thread("agent-b", "user-2", thread_id="t-1")


# ---------------------------------------------------------------------------
# Per-thread TTL override
# ---------------------------------------------------------------------------


class TestInMemoryThreadRegistryPerThreadTTL:
    def test_create_stores_per_thread_ttl(self):
        r = InMemoryThreadRegistry()
        r.create_or_register_thread(
            "agent-a", "user-1", thread_id="t-1", ttl_seconds=300
        )
        assert r._store["t-1"].thread_ttl == 300

    def test_per_thread_ttl_overrides_registry_default(self, monkeypatch):
        r = InMemoryThreadRegistry(default_ttl_seconds=5)
        r.create_or_register_thread(
            "agent-a", "user-1", thread_id="t-1", ttl_seconds=30
        )
        entry = r._store["t-1"]
        monkeypatch.setattr(entry, "last_active", time.monotonic() - 6)
        assert r.get_thread("t-1")["threadId"] == "t-1"

    def test_to_entry_includes_thread_ttl(self):
        r = InMemoryThreadRegistry()
        e = r.create_or_register_thread(
            "agent-a", "user-1", thread_id="t-1", ttl_seconds=120
        )
        assert e["threadTtl"] == 120

    def test_to_entry_thread_ttl_none_when_not_set(self):
        r = InMemoryThreadRegistry()
        e = r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        assert e["threadTtl"] is None

    def test_update_thread_sets_per_thread_ttl(self):
        r = InMemoryThreadRegistry()
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        e = r.update_thread("t-1", ttl_seconds=600)
        assert e["threadTtl"] == 600
        assert r._store["t-1"].thread_ttl == 600

    def test_update_omits_ttl_leaves_per_thread_ttl_unchanged(self):
        r = InMemoryThreadRegistry()
        r.create_or_register_thread(
            "agent-a", "user-1", thread_id="t-1", ttl_seconds=300
        )
        e = r.update_thread("t-1", description="x")
        assert e["threadTtl"] == 300
        assert r._store["t-1"].thread_ttl == 300

    # ── expiresAt field ────────────────────────────────────────────────────────

    def test_expires_at_none_when_no_ttl(self):
        r = InMemoryThreadRegistry()
        e = r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        assert e["expiresAt"] is None

    def test_expires_at_set_when_per_thread_ttl(self):
        r = InMemoryThreadRegistry()
        e = r.create_or_register_thread(
            "agent-a", "user-1", thread_id="t-1", ttl_seconds=300
        )
        assert e["expiresAt"] is not None

    def test_expires_at_set_when_registry_default_ttl(self):
        r = InMemoryThreadRegistry(default_ttl_seconds=600)
        e = r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        assert e["expiresAt"] is not None

    def test_expires_at_slides_on_touch(self, monkeypatch):
        from datetime import datetime, timedelta, timezone

        r = InMemoryThreadRegistry(default_ttl_seconds=3600)
        r.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        entry = r._store["t-1"]
        # Wind wall clock back so the update will produce a strictly later expiresAt
        past_wall = datetime.now(timezone.utc) - timedelta(seconds=60)
        monkeypatch.setattr(entry, "last_active_wall", past_wall)
        before_touch = entry.to_entry(r._default_ttl)["expiresAt"]
        r.update_thread("t-1", description="touched")
        after_touch = r.get_thread("t-1")["expiresAt"]
        assert before_touch is not None
        assert after_touch is not None
        assert after_touch > before_touch


class TestInMemoryThreadRegistryTTLValidation:
    """TTL inputs that are invalid for the service must also be rejected in-memory."""

    @pytest.mark.parametrize("bad", [-1, 0, -100, False, True, 1.5])
    def test_init_rejects_invalid_default_ttl(self, bad):
        with pytest.raises(ValueError, match="ttl_seconds"):
            InMemoryThreadRegistry(default_ttl_seconds=bad)

    @pytest.mark.parametrize("bad", [-1, 0, False, True, 2.0])
    def test_create_rejects_invalid_per_call_ttl(self, bad):
        reg = InMemoryThreadRegistry()
        with pytest.raises(ValueError, match="ttl_seconds"):
            reg.create_or_register_thread("agent", "user", ttl_seconds=bad)

    @pytest.mark.parametrize("bad", [-1, 0, False, True, 3.5])
    def test_update_rejects_invalid_per_call_ttl(self, bad):
        reg = InMemoryThreadRegistry()
        reg.create_or_register_thread("agent", "user", thread_id="t-1")
        with pytest.raises(ValueError, match="ttl_seconds"):
            reg.update_thread("t-1", ttl_seconds=bad)

    def test_valid_positive_integer_accepted(self):
        reg = InMemoryThreadRegistry(default_ttl_seconds=3600)
        entry = reg.create_or_register_thread("agent", "user", ttl_seconds=1800)
        assert entry["threadTtl"] == 1800

    def test_none_is_accepted(self):
        reg = InMemoryThreadRegistry(default_ttl_seconds=None)
        entry = reg.create_or_register_thread("agent", "user", ttl_seconds=None)
        assert entry["expiresAt"] is None


# ---------------------------------------------------------------------------
# Telemetry metrics
# ---------------------------------------------------------------------------

_REQUEST_METRIC = "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
_ERROR_METRIC = "sap_cloud_sdk.core.telemetry.metrics_decorator.record_error_metric"


class TestInMemoryTelemetry:
    """The in-memory registry emits the same metrics as the service-backed one,
    so operation counts are consistent regardless of backend."""

    def test_create_or_register_thread_records_request_metric(self, reg):
        with patch(_REQUEST_METRIC) as metric:
            reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        metric.assert_called_once_with(
            Module.AGENT_MEMORY,
            None,
            Operation.AGENT_MEMORY_CREATE_OR_REGISTER_THREAD,
            False,
        )

    def test_get_thread_records_request_metric(self, reg):
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        with patch(_REQUEST_METRIC) as metric:
            reg.get_thread("t-1")
        metric.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_GET_THREAD, False
        )

    def test_list_threads_records_request_metric(self, reg):
        with patch(_REQUEST_METRIC) as metric:
            reg.list_threads()
        metric.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_LIST_THREADS, False
        )

    def test_update_thread_records_single_request_metric(self, reg):
        """update_thread uses the private _get_live helper, not the decorated
        get_thread, so exactly one metric fires."""
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        with patch(_REQUEST_METRIC) as metric:
            reg.update_thread("t-1", description="new")
        metric.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_UPDATE_THREAD, False
        )

    def test_delete_thread_records_request_metric(self, reg):
        reg.create_or_register_thread("agent-a", "user-1", thread_id="t-1")
        with patch(_REQUEST_METRIC) as metric:
            reg.delete_thread("t-1")
        metric.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_DELETE_THREAD, False
        )

    def test_get_missing_thread_records_error_metric(self, reg):
        with patch(_REQUEST_METRIC) as req, patch(_ERROR_METRIC) as err:
            with pytest.raises(AgentMemoryThreadNotFoundError):
                reg.get_thread("missing")
        err.assert_called_once_with(
            Module.AGENT_MEMORY, None, Operation.AGENT_MEMORY_GET_THREAD, False
        )
        req.assert_not_called()
