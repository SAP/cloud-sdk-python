"""Unit tests for CacheConfig, configure_cache, and get_cache_config."""

import pytest

from sap_cloud_sdk.cache._config import CacheConfig, configure_cache, get_cache_config
from sap_cloud_sdk.cache._lru_backend import InMemoryLRUBackend


class TestGetCacheConfigDefaults:
    def test_get_cache_config_returns_cacheconfig_instance(self) -> None:
        cfg = get_cache_config()
        assert isinstance(cfg, CacheConfig)

    def test_default_config_is_enabled(self) -> None:
        cfg = CacheConfig()
        assert cfg.enabled is True

    def test_default_ttl_seconds(self) -> None:
        assert CacheConfig().default_ttl_seconds == 300

    def test_default_expiry_buffer_seconds(self) -> None:
        assert CacheConfig().expiry_buffer_seconds == 30

    def test_default_max_size(self) -> None:
        assert CacheConfig().max_size == 1000

    def test_default_backend_is_none(self) -> None:
        assert CacheConfig().backend is None

    def test_default_isolation_strategy_is_none(self) -> None:
        assert CacheConfig().isolation_strategy is None


class TestConfigureCache:
    def setup_method(self) -> None:
        # Reset global config to defaults before each test.
        configure_cache(CacheConfig())

    def test_configure_cache_replaces_global_config(self) -> None:
        new_cfg = CacheConfig(default_ttl_seconds=999)
        configure_cache(new_cfg)
        assert get_cache_config().default_ttl_seconds == 999

    def test_configure_cache_with_custom_backend(self) -> None:
        backend = InMemoryLRUBackend(max_size=50)
        configure_cache(CacheConfig(backend=backend))
        assert get_cache_config().backend is backend

    def test_configure_cache_disabled(self) -> None:
        configure_cache(CacheConfig(enabled=False))
        assert get_cache_config().enabled is False

    def test_configure_cache_multiple_times_uses_last(self) -> None:
        configure_cache(CacheConfig(default_ttl_seconds=100))
        configure_cache(CacheConfig(default_ttl_seconds=200))
        assert get_cache_config().default_ttl_seconds == 200

    def teardown_method(self) -> None:
        configure_cache(CacheConfig())
