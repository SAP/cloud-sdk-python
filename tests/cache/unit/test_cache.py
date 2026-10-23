"""Unit tests for the Cache façade."""

from unittest.mock import MagicMock

import pytest

from sap_cloud_sdk.cache._backend import CacheBackend
from sap_cloud_sdk.cache._cache import Cache
from sap_cloud_sdk.cache._config import CacheConfig, configure_cache
from sap_cloud_sdk.cache._isolation import IsolationStrategy
from sap_cloud_sdk.core.runtime_context import APP_TENANT_ID, USER_ID, RuntimeContext
from sap_cloud_sdk.core.runtime_context._context import sdk_context
from sap_cloud_sdk.cache.exceptions import BackendError


def _ctx(tenant_id: str | None = None, user_id: str | None = None) -> RuntimeContext:
    values: dict = {}
    if tenant_id is not None:
        values[APP_TENANT_ID] = tenant_id
    if user_id is not None:
        values[USER_ID] = user_id
    return RuntimeContext(values)


class TestCacheGet:
    def test_get_miss_returns_none(self) -> None:
        cache = Cache(CacheConfig())
        with sdk_context(_ctx(tenant_id="t1")):
            assert cache.get("ns", "key") is None

    def test_get_returns_stored_value(self) -> None:
        cache = Cache(CacheConfig())
        with sdk_context(_ctx(tenant_id="t1")):
            cache.set("ns", "key", "value", ttl_seconds=60)
            assert cache.get("ns", "key") == "value"

    def test_get_disabled_always_returns_none(self) -> None:
        cache = Cache(CacheConfig(enabled=False))
        with sdk_context(_ctx(tenant_id="t1")):
            cache.set("ns", "key", "value", ttl_seconds=60)
            assert cache.get("ns", "key") is None

    def test_get_different_tenants_are_isolated(self) -> None:
        cache = Cache(CacheConfig())
        with sdk_context(_ctx(tenant_id="t1")):
            cache.set("ns", "key", "t1-value", ttl_seconds=60)
        with sdk_context(_ctx(tenant_id="t2")):
            assert cache.get("ns", "key") is None

    def test_get_different_users_are_isolated(self) -> None:
        cache = Cache(CacheConfig())
        with sdk_context(_ctx(tenant_id="t", user_id="u1")):
            cache.set("ns", "key", "u1-value", ttl_seconds=60)
        with sdk_context(_ctx(tenant_id="t", user_id="u2")):
            assert cache.get("ns", "key") is None

    def test_get_swallows_backend_exceptions_and_returns_none(self) -> None:
        bad_backend = MagicMock(spec=CacheBackend)
        bad_backend.get.side_effect = RuntimeError("backend down")
        cache = Cache(CacheConfig(backend=bad_backend))
        with sdk_context(_ctx(tenant_id="t")):
            assert cache.get("ns", "key") is None


class TestCacheSet:
    def test_set_disabled_is_noop(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        cache = Cache(CacheConfig(enabled=False, backend=backend))
        with sdk_context(_ctx(tenant_id="t")):
            cache.set("ns", "key", "v", ttl_seconds=60)
        backend.set.assert_not_called()

    def test_set_applies_expiry_buffer(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        backend.get.return_value = None
        cache = Cache(CacheConfig(expiry_buffer_seconds=10, backend=backend))
        with sdk_context(_ctx(tenant_id="t")):
            cache.set("ns", "key", "v", ttl_seconds=60)
        _, _, forwarded_ttl = backend.set.call_args[0]
        assert forwarded_ttl == 50  # 60 - 10

    def test_set_uses_default_ttl_when_none_given(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        backend.get.return_value = None
        cache = Cache(
            CacheConfig(
                default_ttl_seconds=300, expiry_buffer_seconds=30, backend=backend
            )
        )
        with sdk_context(_ctx(tenant_id="t")):
            cache.set("ns", "key", "v", ttl_seconds=None)
        _, _, forwarded_ttl = backend.set.call_args[0]
        assert forwarded_ttl == 270  # 300 - 30

    def test_set_clamps_negative_effective_ttl_to_one(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        backend.get.return_value = None
        cache = Cache(CacheConfig(expiry_buffer_seconds=100, backend=backend))
        with sdk_context(_ctx(tenant_id="t")):
            cache.set("ns", "key", "v", ttl_seconds=50)
        _, _, forwarded_ttl = backend.set.call_args[0]
        assert forwarded_ttl == 1

    def test_set_raises_backend_error_on_backend_exception(self) -> None:
        bad_backend = MagicMock(spec=CacheBackend)
        bad_backend.set.side_effect = IOError("redis unavailable")
        cache = Cache(CacheConfig(backend=bad_backend))
        with sdk_context(_ctx(tenant_id="t")):
            with pytest.raises(BackendError):
                cache.set("ns", "key", "v", ttl_seconds=60)


class TestCacheEvict:
    def test_evict_removes_entry(self) -> None:
        cache = Cache(CacheConfig())
        with sdk_context(_ctx(tenant_id="t")):
            cache.set("ns", "key", "v", ttl_seconds=60)
            cache.evict("ns", "key")
            assert cache.get("ns", "key") is None

    def test_evict_disabled_is_noop(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        cache = Cache(CacheConfig(enabled=False, backend=backend))
        with sdk_context(_ctx(tenant_id="t")):
            cache.evict("ns", "key")
        backend.delete.assert_not_called()

    def test_evict_swallows_backend_exceptions(self) -> None:
        bad_backend = MagicMock(spec=CacheBackend)
        bad_backend.delete.side_effect = RuntimeError("backend down")
        cache = Cache(CacheConfig(backend=bad_backend))
        with sdk_context(_ctx(tenant_id="t")):
            cache.evict("ns", "key")  # must not raise


class TestCacheReset:
    def test_reset_clears_all_entries(self) -> None:
        cache = Cache(CacheConfig())
        with sdk_context(_ctx(tenant_id="t")):
            cache.set("ns", "a", 1, ttl_seconds=60)
            cache.set("ns", "b", 2, ttl_seconds=60)
            cache.reset()
            assert cache.get("ns", "a") is None
            assert cache.get("ns", "b") is None

    def test_reset_swallows_backend_exceptions(self) -> None:
        bad_backend = MagicMock(spec=CacheBackend)
        bad_backend.clear.side_effect = RuntimeError("backend down")
        cache = Cache(CacheConfig(backend=bad_backend))
        cache.reset()  # must not raise


class TestCacheProviderIsolation:
    def test_provider_strategy_shares_across_tenants(self) -> None:
        cache = Cache(CacheConfig(isolation_strategy=IsolationStrategy.PROVIDER))
        with sdk_context(_ctx(tenant_id="t1")):
            cache.set("csrf", "svc", "token-1", ttl_seconds=60)
        with sdk_context(_ctx(tenant_id="t2")):
            assert cache.get("csrf", "svc") == "token-1"


class TestCachePerClientConfigOverride:
    def setup_method(self) -> None:
        configure_cache(CacheConfig(default_ttl_seconds=300))

    def test_per_client_config_overrides_global(self) -> None:
        backend = MagicMock(spec=CacheBackend)
        backend.get.return_value = None
        per_client = CacheConfig(
            default_ttl_seconds=60, expiry_buffer_seconds=0, backend=backend
        )
        cache = Cache(per_client)
        with sdk_context(_ctx(tenant_id="t")):
            cache.set("ns", "key", "v", ttl_seconds=None)
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
        with sdk_context(_ctx(tenant_id="tenant-xyz")):
            cache.set("destination", "my-dest", "v", ttl_seconds=60)
        full_key = backend.set.call_args[0][0]
        assert full_key.startswith("destination::")
        assert full_key.endswith("::my-dest")
        assert "tenant-xyz" in full_key
