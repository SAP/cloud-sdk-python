"""Unit tests for pluggable token cache implementations."""

import time
from unittest.mock import patch

import pytest

from sap_cloud_sdk.adms._token_cache import InMemoryTokenCache, TokenCache


class TestInMemoryTokenCache:
    def test_get_returns_none_when_empty(self):
        cache = InMemoryTokenCache()
        assert cache.get("key") is None

    def test_set_and_get_returns_token(self):
        cache = InMemoryTokenCache()
        cache.set("cc", "my-token", 3600)
        assert cache.get("cc") == "my-token"

    def test_expired_entry_returns_none(self):
        cache = InMemoryTokenCache()
        cache.set("cc", "my-token", 0)  # TTL = 0 → expires immediately
        # monotonic time may not have advanced; force expiry by patching
        with patch("sap_cloud_sdk.adms._token_cache.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 1
            result = cache.get("cc")
        assert result is None

    def test_set_overwrites_existing_key(self):
        cache = InMemoryTokenCache()
        cache.set("cc", "old-token", 3600)
        cache.set("cc", "new-token", 3600)
        assert cache.get("cc") == "new-token"

    def test_delete_removes_entry(self):
        cache = InMemoryTokenCache()
        cache.set("cc", "my-token", 3600)
        cache.delete("cc")
        assert cache.get("cc") is None

    def test_delete_nonexistent_key_is_safe(self):
        cache = InMemoryTokenCache()
        cache.delete("no-such-key")  # Should not raise

    def test_multiple_keys_are_independent(self):
        cache = InMemoryTokenCache()
        cache.set("cc", "service-token", 3600)
        cache.set("user-jwt-abc", "user-token", 300)
        assert cache.get("cc") == "service-token"
        assert cache.get("user-jwt-abc") == "user-token"

    def test_token_cache_is_abstract(self):
        with pytest.raises(TypeError):
            TokenCache()

    def test_valid_ttl_is_cached(self):
        cache = InMemoryTokenCache()
        cache.set("cc", "tok", 3540)
        assert cache.get("cc") == "tok"
