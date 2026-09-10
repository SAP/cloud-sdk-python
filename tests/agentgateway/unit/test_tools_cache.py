"""Unit tests for MCPToolsCache."""

import time
from unittest.mock import patch

import pytest

from sap_cloud_sdk.agentgateway._models import CacheOptions, MCPTool, MCPToolFilter
from sap_cloud_sdk.agentgateway._tools_cache import MCPToolsCache, _make_cache_key


def _tool(name: str) -> MCPTool:
    return MCPTool(
        name=name,
        server_name="test-server",
        description="desc",
        input_schema={},
        url="https://example.com/mcp",
    )


TOOLS_A = [_tool("tool-a")]
TOOLS_B = [_tool("tool-b"), _tool("tool-c")]
DEFAULT_OPTIONS = CacheOptions()


class TestCacheKey:
    def test_system_and_user_produce_different_keys(self):
        assert _make_cache_key(None, False) != _make_cache_key(None, True)

    def test_filter_ord_ids_included_in_key(self):
        f = MCPToolFilter(ord_ids=["sap.s4:v1", "sap.crm:v2"])
        key = _make_cache_key(f, False)
        assert "sap.s4:v1" in key
        assert "sap.crm:v2" in key

    def test_filter_ord_ids_sorted_for_stability(self):
        f1 = MCPToolFilter(ord_ids=["b", "a"])
        f2 = MCPToolFilter(ord_ids=["a", "b"])
        assert _make_cache_key(f1, False) == _make_cache_key(f2, False)

    def test_filter_names_sorted_for_stability(self):
        f1 = MCPToolFilter(names=["z", "a"])
        f2 = MCPToolFilter(names=["a", "z"])
        assert _make_cache_key(f1, False) == _make_cache_key(f2, False)

    def test_none_filter_and_empty_filter_same_key(self):
        assert _make_cache_key(None, False) == _make_cache_key(MCPToolFilter(), False)

    def test_different_filters_different_keys(self):
        f1 = MCPToolFilter(names=["get-order"])
        f2 = MCPToolFilter(names=["create-order"])
        assert _make_cache_key(f1, False) != _make_cache_key(f2, False)


class TestCacheHitAndMiss:
    def test_miss_on_empty_cache(self):
        c = MCPToolsCache()
        assert c.get(None, False) is None

    def test_hit_after_set(self):
        c = MCPToolsCache()
        c.set(TOOLS_A, None, False, DEFAULT_OPTIONS)
        result = c.get(None, False)
        assert result == TOOLS_A

    def test_miss_for_different_filter(self):
        c = MCPToolsCache()
        c.set(TOOLS_A, None, False, DEFAULT_OPTIONS)
        assert c.get(MCPToolFilter(names=["other"]), False) is None

    def test_miss_for_different_auth_type(self):
        c = MCPToolsCache()
        c.set(TOOLS_A, None, False, DEFAULT_OPTIONS)
        assert c.get(None, True) is None

    def test_independent_entries_for_different_filters(self):
        c = MCPToolsCache()
        f1 = MCPToolFilter(names=["tool-a"])
        f2 = MCPToolFilter(names=["tool-b"])
        c.set(TOOLS_A, f1, False, DEFAULT_OPTIONS)
        c.set(TOOLS_B, f2, False, DEFAULT_OPTIONS)
        assert c.get(f1, False) == TOOLS_A
        assert c.get(f2, False) == TOOLS_B


class TestTTLExpiry:
    def test_expired_entry_returns_none(self):
        c = MCPToolsCache()
        options = CacheOptions(ttl=1.0)
        c.set(TOOLS_A, None, False, options)
        with patch("sap_cloud_sdk.agentgateway._tools_cache.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2.0
            assert c.get(None, False) is None

    def test_valid_entry_within_ttl_is_returned(self):
        c = MCPToolsCache()
        options = CacheOptions(ttl=600.0)
        c.set(TOOLS_A, None, False, options)
        assert c.get(None, False) == TOOLS_A

    def test_expired_entry_is_removed_from_cache(self):
        c = MCPToolsCache()
        options = CacheOptions(ttl=1.0)
        c.set(TOOLS_A, None, False, options)
        with patch("sap_cloud_sdk.agentgateway._tools_cache.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2.0
            c.get(None, False)
        assert len(c._entries) == 0


class TestLruEviction:
    def test_lru_entry_evicted_when_full(self):
        options = CacheOptions(max_size=2)
        c = MCPToolsCache()
        f1 = MCPToolFilter(names=["a"])
        f2 = MCPToolFilter(names=["b"])
        f3 = MCPToolFilter(names=["c"])

        c.set(TOOLS_A, f1, False, options)
        c.set(TOOLS_A, f2, False, options)
        # f1 is now LRU — adding f3 should evict it
        c.set(TOOLS_A, f3, False, options)

        assert c.get(f1, False) is None  # evicted
        assert c.get(f2, False) == TOOLS_A
        assert c.get(f3, False) == TOOLS_A

    def test_get_promotes_entry_to_mru(self):
        options = CacheOptions(max_size=2)
        c = MCPToolsCache()
        f1 = MCPToolFilter(names=["a"])
        f2 = MCPToolFilter(names=["b"])
        f3 = MCPToolFilter(names=["c"])

        c.set(TOOLS_A, f1, False, options)
        c.set(TOOLS_A, f2, False, options)
        # Access f1 to make it MRU; f2 becomes LRU
        c.get(f1, False)
        c.set(TOOLS_A, f3, False, options)

        assert c.get(f1, False) == TOOLS_A  # promoted — not evicted
        assert c.get(f2, False) is None     # evicted


class TestEvict:
    def test_evict_clears_all_entries(self):
        c = MCPToolsCache()
        c.set(TOOLS_A, None, False, DEFAULT_OPTIONS)
        c.set(TOOLS_B, None, True, DEFAULT_OPTIONS)
        c.evict()
        assert c.get(None, False) is None
        assert c.get(None, True) is None

    def test_evict_on_empty_cache_is_noop(self):
        c = MCPToolsCache()
        c.evict()  # should not raise
        assert len(c._entries) == 0

    def test_set_after_evict_works(self):
        c = MCPToolsCache()
        c.set(TOOLS_A, None, False, DEFAULT_OPTIONS)
        c.evict()
        c.set(TOOLS_B, None, False, DEFAULT_OPTIONS)
        assert c.get(None, False) == TOOLS_B


class TestCacheOptionsEvict:
    def test_evict_before_first_use_is_noop(self):
        cache = CacheOptions()
        cache.evict()  # _cache is None — should not raise

    def test_evict_clears_entries_via_cache_options(self):
        cache = CacheOptions()
        cache._cache = MCPToolsCache()
        cache._cache.set(TOOLS_A, None, False, cache)
        cache.evict()
        assert cache._cache.get(None, False) is None

    def test_cache_options_defaults(self):
        cache = CacheOptions()
        assert cache.ttl == 600.0
        assert cache.max_size == 32
        assert cache._cache is None

    def test_cache_options_custom_values(self):
        cache = CacheOptions(ttl=120.0, max_size=5)
        assert cache.ttl == 120.0
        assert cache.max_size == 5
