"""Unit tests for the Cache façade."""

from unittest.mock import MagicMock, call

import pytest

from sap_cloud_sdk.cache._backend import CacheBackend
from sap_cloud_sdk.cache._cache import Cache
from sap_cloud_sdk.cache._config import CacheConfig, configure_cache
from sap_cloud_sdk.cache._isolation import IsolationStrategy
from sap_cloud_sdk.cache._lru_backend import InMemoryLRUBackend
from sap_cloud_sdk.cache.exceptions import BackendError


class TestCacheGet:
    def test_get_miss_returns_none(self) -> None:
        cache = Cache(CacheConfig())
        result = cache.get("ns", "key", tenant_id="t1")
        assert result is None

    def test_get_returns_stored_value(self) -> None:
        cache = Cache(CacheConfig())
        cache.set("ns", "key", "value", ttl_seconds=60, tenant_id="t1")
        assert cache.get("ns", "key", tenant_id="t1") == "value"

    def test_get_disabled_always_returns_none(self) -> None:
        cache = Cache(CacheConfig(enabled=False))
        cache.set("ns", "key", "value", ttl_seconds=60, tenant_id="t1")
        assert cache.get("ns", "key", tenant_id="t1") is None

    def test_get_different_tenants_are_isolated(self) -> None:
        cache = Cache(CacheConfig())
        cache.set("ns", "key", "t1-value", ttl_seconds=60, tenant_id="t1")
        assert cache.get("ns", "key", tenant_id="t2") is None

    def test_get_different_users_are_isolated(self) -> None:
        cache = Cache(CacheConfig())
        cache.set("ns", "key", "u1-value", ttl_seconds=60, tenant_id="t", user_id="u1")
        assert cache.get("ns", "key", tenant_id="t", user_id="u2") is None

    def test_get_swallows_backend_exceptions_and_returns_none(self) -> None:
        bad_backend = MagicMock(spec=CacheBackend)
        bad_backend.get.side_effect = RuntimeError("backend down")
        cache = Cache(CacheConfig(backend=bad_backend))
        assert cache.get("ns", "key", tenant_id="t") is None


class TestCacheSet:
    def test_set_disabled_is_noop(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        cache = Cache(CacheConfig(enabled=False, backend=backend))
        cache.set("ns", "key", "v", ttl_seconds=60, tenant_id="t")
        backend.set.assert_not_called()

    def test_set_applies_expiry_buffer(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        backend.get.return_value = None
        cache = Cache(CacheConfig(expiry_buffer_seconds=10, backend=backend))
        cache.set("ns", "key", "v", ttl_seconds=60, tenant_id="t")
        _, _, forwarded_ttl = backend.set.call_args[0]
        assert forwarded_ttl == 50  # 60 - 10

    def test_set_uses_default_ttl_when_none_given(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        backend.get.return_value = None
        cache = Cache(
            CacheConfig(default_ttl_seconds=300, expiry_buffer_seconds=30, backend=backend)
        )
        cache.set("ns", "key", "v", ttl_seconds=None, tenant_id="t")
        _, _, forwarded_ttl = backend.set.call_args[0]
        assert forwarded_ttl == 270  # 300 - 30

    def test_set_clamps_negative_effective_ttl_to_one(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        backend.get.return_value = None
        cache = Cache(CacheConfig(expiry_buffer_seconds=100, backend=backend))
        cache.set("ns", "key", "v", ttl_seconds=50, tenant_id="t")
        _, _, forwarded_ttl = backend.set.call_args[0]
        assert forwarded_ttl == 1

    def test_set_raises_backend_error_on_backend_exception(self) -> None:
        bad_backend = MagicMock(spec=CacheBackend)
        bad_backend.set.side_effect = IOError("redis unavailable")
        cache = Cache(CacheConfig(backend=bad_backend))
        with pytest.raises(BackendError):
            cache.set("ns", "key", "v", ttl_seconds=60, tenant_id="t")


class TestCacheEvict:
    def test_evict_removes_entry(self) -> None:
        cache = Cache(CacheConfig())
        cache.set("ns", "key", "v", ttl_seconds=60, tenant_id="t")
        cache.evict("ns", "key", tenant_id="t")
        assert cache.get("ns", "key", tenant_id="t") is None

    def test_evict_disabled_is_noop(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        cache = Cache(CacheConfig(enabled=False, backend=backend))
        cache.evict("ns", "key", tenant_id="t")
        backend.delete.assert_not_called()

    def test_evict_swallows_backend_exceptions(self) -> None:
        bad_backend = MagicMock(spec=CacheBackend)
        bad_backend.delete.side_effect = RuntimeError("backend down")
        cache = Cache(CacheConfig(backend=bad_backend))
        cache.evict("ns", "key", tenant_id="t")  # must not raise


class TestCacheReset:
    def test_reset_clears_all_entries(self) -> None:
        cache = Cache(CacheConfig())
        cache.set("ns", "a", 1, ttl_seconds=60, tenant_id="t")
        cache.set("ns", "b", 2, ttl_seconds=60, tenant_id="t")
        cache.reset()
        assert cache.get("ns", "a", tenant_id="t") is None
        assert cache.get("ns", "b", tenant_id="t") is None

    def test_reset_swallows_backend_exceptions(self) -> None:
        bad_backend = MagicMock(spec=CacheBackend)
        bad_backend.clear.side_effect = RuntimeError("backend down")
        cache = Cache(CacheConfig(backend=bad_backend))
        cache.reset()  # must not raise


class TestCachePerClientConfigOverride:
    def setup_method(self) -> None:
        configure_cache(CacheConfig(default_ttl_seconds=300))

    def test_per_client_config_overrides_global(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        backend.get.return_value = None
        per_client = CacheConfig(default_ttl_seconds=60, expiry_buffer_seconds=0, backend=backend)
        cache = Cache(per_client)
        cache.set("ns", "key", "v", ttl_seconds=None, tenant_id="t")
        _, _, forwarded_ttl = backend.set.call_args[0]
        assert forwarded_ttl == 60  # uses per-client default, not global 300

    def teardown_method(self) -> None:
        configure_cache(CacheConfig())


class TestCacheFullKeyStructure:
    def test_full_key_includes_namespace_and_key(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        backend.get.return_value = None
        cache = Cache(
            CacheConfig(
                isolation_strategy=IsolationStrategy.TENANT,
                backend=backend,
            )
        )
        cache.set("destination", "my-dest", "v", ttl_seconds=60, tenant_id="tenant-xyz")
        full_key = backend.set.call_args[0][0]
        assert full_key.startswith("destination::")
        assert full_key.endswith("::my-dest")
        assert "tenant-xyz" in full_key
