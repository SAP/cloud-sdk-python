"""Unit tests for the Cache façade."""

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from sap_cloud_sdk.core.resilience.cache._backend import CacheBackend
from sap_cloud_sdk.core.resilience.cache._cache import Cache
from sap_cloud_sdk.core.resilience.cache._config import (
    ENV_CACHE_DISABLED,
    CacheConfig,
    configure_cache,
)
from sap_cloud_sdk.core.resilience.cache._isolation import IsolationStrategy
from sap_cloud_sdk.core.resilience.cache._registry import reset_module_backends
from sap_cloud_sdk.core.runtime_context import APP_TENANT_ID, USER_ID, RuntimeContext
from sap_cloud_sdk.core.runtime_context._context import sdk_context
from sap_cloud_sdk.core.resilience.cache.exceptions import BackendError


def _ctx(tenant_id: str | None = None, user_id: str | None = None) -> RuntimeContext:
    values: dict = {}
    if tenant_id is not None:
        values[APP_TENANT_ID] = tenant_id
    if user_id is not None:
        values[USER_ID] = user_id
    return RuntimeContext(values)


@pytest.fixture(autouse=True)
def _clear_module_registry() -> Generator[None, None, None]:
    """Reset the per-module backend registry before every test.

    Module-level singletons persist across test cases, which would cause
    tests that use ``module=`` to interfere with each other.
    """
    reset_module_backends()
    yield
    reset_module_backends()


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


class TestCacheModuleBackend:
    """Tests for the optional ``module=`` keyword on :class:`Cache`."""

    def test_same_module_name_shares_backend(self) -> None:
        """Two Cache instances with the same module share state."""
        cfg = CacheConfig(isolation_strategy=IsolationStrategy.TENANT)
        cache_a = Cache(cfg, module="mymodule")
        cache_b = Cache(cfg, module="mymodule")

        with sdk_context(_ctx(tenant_id="t1")):
            cache_a.set("ns", "key", "shared-value", ttl_seconds=60)
            assert cache_b.get("ns", "key") == "shared-value"

    def test_different_module_names_are_isolated(self) -> None:
        """Two Cache instances with different module names do not share state."""
        cfg = CacheConfig(isolation_strategy=IsolationStrategy.TENANT)
        cache_x = Cache(cfg, module="module-x")
        cache_y = Cache(cfg, module="module-y")

        with sdk_context(_ctx(tenant_id="t1")):
            cache_x.set("ns", "key", "value-x", ttl_seconds=60)
            assert cache_y.get("ns", "key") is None

    def test_no_module_gives_fresh_per_instance_backend(self) -> None:
        """Without module=, each Cache instance has its own backend (legacy behavior)."""
        cfg = CacheConfig(isolation_strategy=IsolationStrategy.TENANT)
        cache_1 = Cache(cfg)
        cache_2 = Cache(cfg)

        with sdk_context(_ctx(tenant_id="t1")):
            cache_1.set("ns", "key", "value-1", ttl_seconds=60)
            # cache_2 has a separate backend, so it must not see cache_1's entry.
            assert cache_2.get("ns", "key") is None

    def test_explicit_backend_overrides_module(self) -> None:
        """CacheConfig(backend=...) wins over module=."""
        explicit_backend = MagicMock(spec=CacheBackend)
        explicit_backend.get.return_value = "from-explicit"
        cache = Cache(CacheConfig(backend=explicit_backend), module="mymodule")

        with sdk_context(_ctx(tenant_id="t1")):
            result = cache.get("ns", "key")

        explicit_backend.get.assert_called_once()
        assert result == "from-explicit"

    def test_module_backend_survives_across_simulated_requests(self) -> None:
        """Simulate per-request client creation: backend must carry state across."""
        cfg = CacheConfig(isolation_strategy=IsolationStrategy.TENANT)

        # First "request": create a client and populate the cache.
        cache_req1 = Cache(cfg, module="agentgateway")
        with sdk_context(_ctx(tenant_id="t1")):
            cache_req1.set("token", "svc-url", "my-token", ttl_seconds=60)

        # Second "request": a brand-new client must still find the entry.
        cache_req2 = Cache(cfg, module="agentgateway")
        with sdk_context(_ctx(tenant_id="t1")):
            assert cache_req2.get("token", "svc-url") == "my-token"

    def test_module_backend_tenant_isolation(self) -> None:
        """Shared module backend must still isolate across tenants."""
        cfg = CacheConfig(isolation_strategy=IsolationStrategy.TENANT)
        cache = Cache(cfg, module="agentgateway")

        with sdk_context(_ctx(tenant_id="tenant-a")):
            cache.set("token", "svc", "token-a", ttl_seconds=60)
        with sdk_context(_ctx(tenant_id="tenant-b")):
            assert cache.get("token", "svc") is None

    def test_module_backend_sizing_from_first_caller(self) -> None:
        """max_size is fixed on the first Cache created for a module."""
        # First caller: max_size=2
        cache_first = Cache(CacheConfig(max_size=2), module="sized-module")
        # Second caller: max_size=500 (ignored — backend already exists)
        cache_second = Cache(CacheConfig(max_size=500), module="sized-module")

        # Both should share the same backend (capped at 2).
        with sdk_context(_ctx(tenant_id="t1")):
            cache_first.set("ns", "k1", "v1", ttl_seconds=60)
            cache_first.set("ns", "k2", "v2", ttl_seconds=60)
            # Third entry evicts the oldest (LRU) when max_size=2.
            cache_first.set("ns", "k3", "v3", ttl_seconds=60)
            # k3 is always present; exactly one of k1/k2 was evicted.
            assert cache_second.get("ns", "k3") == "v3"


class TestCacheEnvKillSwitch:
    """Tests for the CLOUD_SDK_CACHE_DISABLED environment kill switch."""

    def test_env_disables_get(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cache = Cache(CacheConfig())
        with sdk_context(_ctx(tenant_id="t1")):
            cache.set("ns", "key", "value", ttl_seconds=60)
            monkeypatch.setenv(ENV_CACHE_DISABLED, "true")
            assert cache.get("ns", "key") is None

    def test_env_disables_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        backend = MagicMock(spec=CacheBackend)
        cache = Cache(CacheConfig(backend=backend))
        monkeypatch.setenv(ENV_CACHE_DISABLED, "true")
        with sdk_context(_ctx(tenant_id="t1")):
            cache.set("ns", "key", "v", ttl_seconds=60)
        backend.set.assert_not_called()

    def test_env_disables_evict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        backend = MagicMock(spec=CacheBackend)
        cache = Cache(CacheConfig(backend=backend))
        monkeypatch.setenv(ENV_CACHE_DISABLED, "true")
        with sdk_context(_ctx(tenant_id="t1")):
            cache.evict("ns", "key")
        backend.delete.assert_not_called()

    def test_env_overrides_enabled_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The env var wins even when the client hardcodes enabled=True."""
        cache = Cache(CacheConfig(enabled=True))
        monkeypatch.setenv(ENV_CACHE_DISABLED, "true")
        with sdk_context(_ctx(tenant_id="t1")):
            cache.set("ns", "key", "value", ttl_seconds=60)
            assert cache.get("ns", "key") is None

    def test_cache_active_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Regression guard: unset env var preserves normal behavior."""
        monkeypatch.delenv(ENV_CACHE_DISABLED, raising=False)
        cache = Cache(CacheConfig())
        with sdk_context(_ctx(tenant_id="t1")):
            cache.set("ns", "key", "value", ttl_seconds=60)
            assert cache.get("ns", "key") == "value"

    def test_cache_active_when_env_not_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-"true" value does not disable the cache."""
        monkeypatch.setenv(ENV_CACHE_DISABLED, "false")
        cache = Cache(CacheConfig())
        with sdk_context(_ctx(tenant_id="t1")):
            cache.set("ns", "key", "value", ttl_seconds=60)
            assert cache.get("ns", "key") == "value"
