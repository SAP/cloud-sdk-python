"""Unit tests for pluggable token cache implementations."""

import time
from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.adms._token_cache import InMemoryTokenCache, RedisTokenCache, TokenCache


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


class TestRedisTokenCache:
    def _make_redis_mock(self, get_return=None):
        mock_redis = MagicMock()
        mock_redis.get.return_value = get_return
        return mock_redis

    def test_import_error_without_redis_package(self):
        with patch.dict("sys.modules", {"redis": None}):
            with pytest.raises(ImportError, match="pip install redis"):
                RedisTokenCache(host="localhost")

    def test_get_returns_token_from_redis(self):
        mock_redis_cls = MagicMock()
        mock_redis_instance = self._make_redis_mock(get_return="cached-token")
        mock_redis_cls.return_value = mock_redis_instance

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}):
            cache = RedisTokenCache(host="localhost", ssl=False)
            result = cache.get("cc")

        assert result == "cached-token"
        mock_redis_instance.get.assert_called_once_with("sap_sdk:tokens:cc")

    def test_set_calls_redis_setex(self):
        mock_redis_cls = MagicMock()
        mock_redis_instance = self._make_redis_mock()
        mock_redis_cls.return_value = mock_redis_instance

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}):
            cache = RedisTokenCache(host="localhost", ssl=False)
            cache.set("cc", "my-token", 3540)

        mock_redis_instance.setex.assert_called_once_with(
            "sap_sdk:tokens:cc", 3540, "my-token"
        )

    def test_delete_calls_redis_delete(self):
        mock_redis_cls = MagicMock()
        mock_redis_instance = self._make_redis_mock()
        mock_redis_cls.return_value = mock_redis_instance

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}):
            cache = RedisTokenCache(host="localhost", ssl=False)
            cache.delete("cc")

        mock_redis_instance.delete.assert_called_once_with("sap_sdk:tokens:cc")

    def test_get_redis_failure_returns_none(self, caplog):
        import logging

        mock_redis_cls = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.side_effect = Exception("Redis connection refused")
        mock_redis_cls.return_value = mock_redis_instance

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}):
            cache = RedisTokenCache(host="localhost", ssl=False)
            with caplog.at_level(
                logging.WARNING, logger="sap_cloud_sdk.adms._token_cache"
            ):
                result = cache.get("cc")

        assert result is None  # Non-fatal — falls through to fresh fetch
        # Operator must have a signal that the cache is silently degrading.
        assert any("RedisTokenCache.get failed" in r.message for r in caplog.records)

    def test_set_redis_failure_is_nonfatal(self, caplog):
        import logging

        mock_redis_cls = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_instance.setex.side_effect = Exception("connection lost")
        mock_redis_cls.return_value = mock_redis_instance

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}):
            cache = RedisTokenCache(host="localhost", ssl=False)
            with caplog.at_level(
                logging.WARNING, logger="sap_cloud_sdk.adms._token_cache"
            ):
                cache.set("cc", "some-token", 3540)  # Should NOT raise

        assert any("RedisTokenCache.set failed" in r.message for r in caplog.records)

    def test_delete_redis_failure_is_nonfatal(self, caplog):
        import logging

        mock_redis_cls = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_instance.delete.side_effect = Exception("connection lost")
        mock_redis_cls.return_value = mock_redis_instance

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}):
            cache = RedisTokenCache(host="localhost", ssl=False)
            with caplog.at_level(
                logging.WARNING, logger="sap_cloud_sdk.adms._token_cache"
            ):
                cache.delete("cc")  # Should NOT raise

        assert any(
            "RedisTokenCache.delete failed" in r.message for r in caplog.records
        )

    def test_custom_key_prefix(self):
        mock_redis_cls = MagicMock()
        mock_redis_instance = self._make_redis_mock()
        mock_redis_cls.return_value = mock_redis_instance

        with patch.dict("sys.modules", {"redis": MagicMock(Redis=mock_redis_cls)}):
            cache = RedisTokenCache(host="localhost", ssl=False, key_prefix="my:prefix:")
            cache.get("cc")

        mock_redis_instance.get.assert_called_once_with("my:prefix:cc")
