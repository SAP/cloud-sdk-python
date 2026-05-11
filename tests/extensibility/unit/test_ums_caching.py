"""Tests for UMS transport TTL cache."""

from unittest.mock import MagicMock, patch

import pytest

from sap_cloud_sdk.extensibility._ums_transport import (
    UmsTransport,
    _CACHE_TTL_SECONDS,
    _CACHE_MAX_SIZE,
    ENV_CONHOS_LANDSCAPE,
)
from sap_cloud_sdk.extensibility.exceptions import TransportError

from tests.extensibility.unit._ums_test_helpers import (
    AGENT_ORD_ID,
    UMS_RESPONSE_SINGLE,
    UMS_RESPONSE_MULTIPLE,
    UMS_RESPONSE_DIFFERENT_CAPABILITY,
    _make_config,
    _make_dest,
    _make_httpx_response,
)


class TestUmsTransportCache:
    """Tests for the UMS transport TTL cache."""

    @pytest.fixture(autouse=True)
    def _set_landscape_env(self, monkeypatch):
        monkeypatch.setenv(ENV_CONHOS_LANDSCAPE, "exttest-dev-eu12")

    @patch("sap_cloud_sdk.extensibility._ums_transport.create_destination_client")
    def _make_transport(self, mock_dest_client, dest=None):
        config = _make_config()
        if dest is None:
            dest = _make_dest()
        mock_dest_client.return_value.get_destination.return_value = dest
        transport = UmsTransport(AGENT_ORD_ID, config)
        return transport, mock_dest_client.return_value

    def _patch_httpx(self, response):
        """Return a context manager that patches httpx.Client to return *response*."""
        patcher = patch("sap_cloud_sdk.extensibility._ums_transport.httpx.Client")
        mock_client_cls = patcher.start()
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = response
        return patcher, mock_client

    def test_cache_hit_returns_cached_result(self):
        """Second call with same capability_id returns cached result without HTTP."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_SINGLE)
        patcher, mock_client = self._patch_httpx(response)

        try:
            result1 = transport.get_extension_capability_implementation()
            result2 = transport.get_extension_capability_implementation()
        finally:
            patcher.stop()

        # Only one HTTP call should have been made
        assert mock_client.post.call_count == 1
        # Both results should be equal (not identical, since we transform on each read)
        assert result1 == result2
        assert result1.extension_names == ["ServiceNow Extension"]

    def test_cache_miss_on_different_capability_id(self):
        """Different capability_id keys do not share cache entries."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_DIFFERENT_CAPABILITY)
        patcher, mock_client = self._patch_httpx(response)

        try:
            result1 = transport.get_extension_capability_implementation(
                capability_id="default"
            )
            result2 = transport.get_extension_capability_implementation(
                capability_id="onboarding"
            )
        finally:
            patcher.stop()

        # Two HTTP calls -- one per distinct capability_id
        assert mock_client.post.call_count == 2
        assert result1.capability_id == "default"
        assert result2.capability_id == "onboarding"

    @patch("sap_cloud_sdk.extensibility._ums_transport.time")
    def test_cache_expires_after_ttl(self, mock_time):
        """After TTL expiry the next call fetches fresh data from UMS."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_SINGLE)
        patcher, mock_client = self._patch_httpx(response)

        # First call at t=0
        mock_time.monotonic.return_value = 0.0
        try:
            result1 = transport.get_extension_capability_implementation()
            assert mock_client.post.call_count == 1

            # Second call at t=599 (within TTL) -- should be cached
            mock_time.monotonic.return_value = 599.0
            result2 = transport.get_extension_capability_implementation()
            assert mock_client.post.call_count == 1
            assert result2 == result1

            # Third call at t=601 (past TTL) -- should fetch fresh
            mock_time.monotonic.return_value = 601.0
            transport.get_extension_capability_implementation()
            assert mock_client.post.call_count == 2
        finally:
            patcher.stop()

    def test_skip_cache_bypasses_cache(self):
        """skip_cache=True always triggers an HTTP call even with a valid cache entry."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_SINGLE)
        patcher, mock_client = self._patch_httpx(response)

        try:
            # Populate cache
            transport.get_extension_capability_implementation()
            assert mock_client.post.call_count == 1

            # skip_cache=True should bypass
            transport.get_extension_capability_implementation(skip_cache=True)
            assert mock_client.post.call_count == 2
        finally:
            patcher.stop()

    def test_skip_cache_updates_cache(self):
        """After skip_cache=True, the fresh result is written to cache for later reads."""
        transport, _ = self._make_transport()

        response1 = _make_httpx_response(UMS_RESPONSE_SINGLE)
        response2 = _make_httpx_response(UMS_RESPONSE_MULTIPLE)

        patcher = patch("sap_cloud_sdk.extensibility._ums_transport.httpx.Client")
        mock_client_cls = patcher.start()
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        # First call returns SINGLE, second (skip_cache) returns MULTIPLE
        mock_client.post.side_effect = [response1, response2]

        try:
            # Populate cache with SINGLE
            result1 = transport.get_extension_capability_implementation()
            assert result1.extension_names == ["ServiceNow Extension"]

            # skip_cache=True fetches MULTIPLE and updates cache
            result2 = transport.get_extension_capability_implementation(skip_cache=True)
            assert result2.extension_names == ["ServiceNow Extension", "Jira Extension"]

            # Normal call should now return the MULTIPLE result from cache
            result3 = transport.get_extension_capability_implementation()
            assert result3 == result2
            # Only 2 HTTP calls total (the third was a cache hit)
            assert mock_client.post.call_count == 2
        finally:
            patcher.stop()

    def test_cache_not_populated_on_error(self):
        """If the UMS call fails, nothing is cached."""
        transport, dest_client = self._make_transport()
        error_response = _make_httpx_response({"error": "fail"}, status_code=500)
        success_response = _make_httpx_response(UMS_RESPONSE_SINGLE)

        patcher = patch("sap_cloud_sdk.extensibility._ums_transport.httpx.Client")
        mock_client_cls = patcher.start()
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = [error_response, success_response]

        try:
            # First call fails
            with pytest.raises(TransportError):
                transport.get_extension_capability_implementation()

            # Cache should be empty, so second call makes a real HTTP request
            result = transport.get_extension_capability_implementation()
            assert result.extension_names == ["ServiceNow Extension"]
            assert mock_client.post.call_count == 2
        finally:
            patcher.stop()

    def test_cache_ttl_constant_is_ten_minutes(self):
        """Sanity check that the TTL constant is 600 seconds (10 minutes)."""
        assert _CACHE_TTL_SECONDS == 600

    def test_cache_isolated_by_tenant(self):
        """Same capability_id but different tenants produce separate cache entries."""
        transport, _ = self._make_transport()

        response1 = _make_httpx_response(UMS_RESPONSE_SINGLE)
        response2 = _make_httpx_response(UMS_RESPONSE_MULTIPLE)

        patcher = patch("sap_cloud_sdk.extensibility._ums_transport.httpx.Client")
        mock_client_cls = patcher.start()
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = [response1, response2]

        try:
            result_a = transport.get_extension_capability_implementation(
                tenant="tenant-a"
            )
            result_b = transport.get_extension_capability_implementation(
                tenant="tenant-b"
            )
        finally:
            patcher.stop()

        # Two HTTP calls -- one per tenant
        assert mock_client.post.call_count == 2
        assert result_a.extension_names == ["ServiceNow Extension"]
        assert result_b.extension_names == ["ServiceNow Extension", "Jira Extension"]

    def test_cache_hit_same_tenant(self):
        """Second call with the same tenant returns cached result."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_SINGLE)
        patcher, mock_client = self._patch_httpx(response)

        try:
            result1 = transport.get_extension_capability_implementation(
                tenant="tenant-a"
            )
            result2 = transport.get_extension_capability_implementation(
                tenant="tenant-a"
            )
        finally:
            patcher.stop()

        assert mock_client.post.call_count == 1
        assert result1 == result2

    def test_different_tenants_are_separate_cache_keys(self):
        """Different tenant values produce separate cache entries."""
        transport, _ = self._make_transport()

        response1 = _make_httpx_response(UMS_RESPONSE_SINGLE)
        response2 = _make_httpx_response(UMS_RESPONSE_MULTIPLE)

        patcher = patch("sap_cloud_sdk.extensibility._ums_transport.httpx.Client")
        mock_client_cls = patcher.start()
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = [response1, response2]

        try:
            result_a = transport.get_extension_capability_implementation(
                tenant="tenant-a"
            )
            result_b = transport.get_extension_capability_implementation(
                tenant="tenant-b"
            )
        finally:
            patcher.stop()

        assert mock_client.post.call_count == 2
        assert result_a is not result_b

    def test_cache_max_size_constant(self):
        """Sanity check that the max size constant is 256."""
        assert _CACHE_MAX_SIZE == 256

    def test_cache_evicts_oldest_when_full(self):
        """When cache reaches max size, the least-recently-used entry is evicted."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_SINGLE)

        patcher, mock_client = self._patch_httpx(response)
        try:
            # Fill the cache to _CACHE_MAX_SIZE entries with distinct tenants
            for i in range(_CACHE_MAX_SIZE):
                transport.get_extension_capability_implementation(tenant=f"tenant-{i}")
            assert len(transport._cache) == _CACHE_MAX_SIZE

            # One more insert should evict the oldest (tenant-0)
            transport.get_extension_capability_implementation(tenant="tenant-new")
            assert len(transport._cache) == _CACHE_MAX_SIZE
            assert ("tenant-0", "default") not in transport._cache
            assert ("tenant-new", "default") in transport._cache
        finally:
            patcher.stop()

    @patch("sap_cloud_sdk.extensibility._ums_transport.time.monotonic")
    def test_cache_sweeps_expired_entries_on_insert(self, mock_time):
        """Expired entries are removed when a new entry is inserted."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_SINGLE)

        patcher, mock_client = self._patch_httpx(response)
        try:
            # Insert at t=0
            mock_time.return_value = 0.0
            transport.get_extension_capability_implementation(tenant="old-tenant")
            assert len(transport._cache) == 1

            # Insert at t=TTL+1 -- old entry should be swept
            mock_time.return_value = _CACHE_TTL_SECONDS + 1
            transport.get_extension_capability_implementation(tenant="new-tenant")
            assert ("old-tenant", "default") not in transport._cache
            assert ("new-tenant", "default") in transport._cache
        finally:
            patcher.stop()

    def test_cache_hit_refreshes_lru_position(self):
        """A cache hit moves the entry to the end so it is not evicted first."""
        transport, _ = self._make_transport()
        response = _make_httpx_response(UMS_RESPONSE_SINGLE)

        patcher, mock_client = self._patch_httpx(response)
        try:
            # Fill cache: tenant-0 is oldest, tenant-1, tenant-2, ...
            for i in range(_CACHE_MAX_SIZE):
                transport.get_extension_capability_implementation(tenant=f"tenant-{i}")
            assert len(transport._cache) == _CACHE_MAX_SIZE

            # Access tenant-0 so it becomes most-recently-used
            transport.get_extension_capability_implementation(tenant="tenant-0")

            # Insert a new entry -- should evict tenant-1 (now the oldest), not tenant-0
            transport.get_extension_capability_implementation(tenant="tenant-new")
            assert ("tenant-0", "default") in transport._cache
            assert ("tenant-1", "default") not in transport._cache
            assert ("tenant-new", "default") in transport._cache
        finally:
            patcher.stop()

