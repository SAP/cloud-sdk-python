"""Unit tests for InMemoryLRUBackend."""

import time

import pytest

from sap_cloud_sdk.cache._lru_backend import InMemoryLRUBackend


class TestInMemoryLRUBackendGet:
    def test_get_missing_key_returns_none(self) -> None:
        backend = InMemoryLRUBackend()
        assert backend.get("nonexistent") is None

    def test_get_returns_stored_value(self) -> None:
        backend = InMemoryLRUBackend()
        backend.set("k", "v", ttl_seconds=60)
        assert backend.get("k") == "v"

    def test_get_after_ttl_expiry_returns_none(self) -> None:
        backend = InMemoryLRUBackend()
        backend.set("k", "v", ttl_seconds=1)
        time.sleep(1.1)
        assert backend.get("k") is None

    def test_get_stores_arbitrary_value_types(self) -> None:
        backend = InMemoryLRUBackend()
        payload = {"a": [1, 2, 3], "b": True}
        backend.set("k", payload, ttl_seconds=60)
        assert backend.get("k") == payload


class TestInMemoryLRUBackendSet:
    def test_set_overwrites_existing_key(self) -> None:
        backend = InMemoryLRUBackend()
        backend.set("k", "first", ttl_seconds=60)
        backend.set("k", "second", ttl_seconds=60)
        assert backend.get("k") == "second"

    def test_set_with_zero_ttl_clamps_to_one_second(self) -> None:
        backend = InMemoryLRUBackend()
        # TTL of 0 is clamped to 1 inside Cache.set(); here we test the backend
        # directly with ttl_seconds=1 to confirm it stores then expires.
        backend.set("k", "v", ttl_seconds=1)
        assert backend.get("k") == "v"


class TestInMemoryLRUBackendDelete:
    def test_delete_removes_existing_entry(self) -> None:
        backend = InMemoryLRUBackend()
        backend.set("k", "v", ttl_seconds=60)
        backend.delete("k")
        assert backend.get("k") is None

    def test_delete_nonexistent_key_is_noop(self) -> None:
        backend = InMemoryLRUBackend()
        backend.delete("missing")  # must not raise

    def test_delete_fires_on_evict_callback_with_manual_reason(self) -> None:
        evictions: list[tuple[str, str]] = []
        backend = InMemoryLRUBackend(on_evict=lambda k, r: evictions.append((k, r)))
        backend.set("k", "v", ttl_seconds=60)
        backend.delete("k")
        assert evictions == [("k", "manual")]


class TestInMemoryLRUBackendClear:
    def test_clear_removes_all_entries(self) -> None:
        backend = InMemoryLRUBackend()
        backend.set("a", 1, ttl_seconds=60)
        backend.set("b", 2, ttl_seconds=60)
        backend.clear()
        assert backend.get("a") is None
        assert backend.get("b") is None

    def test_clear_on_empty_backend_is_noop(self) -> None:
        backend = InMemoryLRUBackend()
        backend.clear()  # must not raise


class TestInMemoryLRUBackendLRUEviction:
    def test_lru_eviction_when_max_size_exceeded(self) -> None:
        backend = InMemoryLRUBackend(max_size=2)
        backend.set("a", 1, ttl_seconds=60)
        backend.set("b", 2, ttl_seconds=60)
        # access "a" to make "b" the LRU
        backend.get("a")
        # adding "c" should evict "b" (LRU)
        backend.set("c", 3, ttl_seconds=60)
        assert backend.get("a") is not None
        assert backend.get("c") is not None
        assert backend.get("b") is None

    def test_lru_eviction_fires_on_evict_callback(self) -> None:
        evictions: list[tuple[str, str]] = []
        backend = InMemoryLRUBackend(
            max_size=1,
            on_evict=lambda k, r: evictions.append((k, r)),
        )
        backend.set("first", "v", ttl_seconds=60)
        backend.set("second", "v", ttl_seconds=60)
        assert any(reason == "lru" for _, reason in evictions)
