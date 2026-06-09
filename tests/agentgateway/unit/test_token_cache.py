"""Unit tests for token cache helpers with non-trivial logic.

Cache class behavior is tested through AgentGatewayClient in other files.
Only helper logic and scope-key semantics are exercised directly here.
"""

import base64
import json
import time
from unittest.mock import patch

from sap_cloud_sdk.agentgateway._token_cache import (
    _TokenCache,
    _parse_jwt_exp,
    compute_expires_at,
)
from sap_cloud_sdk.agentgateway.config import ClientConfig


def _make_jwt(claims: dict) -> str:
    """Build a non-signed JWT for testing (header.payload.signature)."""
    header = base64.urlsafe_b64encode(json.dumps({
        "alg": "none"
    }).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(
        json.dumps(claims).encode()).rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}.signature"


class TestParseJwtExp:
    """Tests for the unverified JWT `exp` claim parser."""

    def test_extracts_exp(self):
        """Extract `exp` claim from a well-formed JWT payload."""
        jwt = _make_jwt({"exp": 1700000000, "iat": 1699996400})
        assert _parse_jwt_exp(jwt) == 1700000000

    def test_returns_none_when_exp_missing(self):
        """Return None when payload has no `exp` claim."""
        jwt = _make_jwt({"iat": 1699996400})
        assert _parse_jwt_exp(jwt) is None

    def test_returns_none_for_malformed_jwt(self):
        """Return None for strings that are not valid JWTs."""
        assert _parse_jwt_exp("not-a-jwt") is None
        assert _parse_jwt_exp("") is None
        assert _parse_jwt_exp("only.two") is None

    def test_returns_none_for_garbage_payload(self):
        """Return None when the payload segment is not valid base64 or JSON."""
        assert _parse_jwt_exp("aaa.@@not-base64@@.bbb") is None


class TestComputeExpiresAt:
    """Tests for cache expiry resolution from token responses."""

    def test_prefers_response_expires_at(self):
        """Use expires_at before other response metadata."""
        cfg = ClientConfig(token_expiry_buffer_seconds=30.0)
        token_data = {
            "expires_at": "1600",
            "expires_in": 999,
            "access_token": _make_jwt({"exp": 1900}),
        }

        with (
                patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                      return_value=1000.0),
                patch(
                    "sap_cloud_sdk.agentgateway._token_cache.time.monotonic",
                    return_value=50.0,
                ),
        ):
            result = compute_expires_at(token_data, cfg)

        assert result == 620.0

    def test_uses_expires_in_when_present(self):
        """Prefer expires_in when no absolute expiry is present."""
        cfg = ClientConfig(token_expiry_buffer_seconds=15.0)

        with patch(
                "sap_cloud_sdk.agentgateway._token_cache.time.monotonic",
                return_value=20.0,
        ):
            result = compute_expires_at({"expires_in": 120}, cfg)

        assert result == 125.0

    def test_falls_back_to_access_token_exp(self):
        """Use access_token exp before id_token or fallback TTL."""
        cfg = ClientConfig(token_expiry_buffer_seconds=30.0)
        token_data = {
            "access_token": _make_jwt({"exp": 1500}),
            "id_token": _make_jwt({"exp": 1700}),
        }

        with (
                patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                      return_value=1000.0),
                patch(
                    "sap_cloud_sdk.agentgateway._token_cache.time.monotonic",
                    return_value=75.0,
                ),
        ):
            result = compute_expires_at(token_data, cfg)

        assert result == 545.0

    def test_falls_back_to_id_token_exp(self):
        """Use id_token exp when the access token is opaque."""
        cfg = ClientConfig(token_expiry_buffer_seconds=30.0)
        token_data = {
            "access_token": "opaque-token",
            "id_token": _make_jwt({"exp": 1400}),
        }

        with (
                patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                      return_value=1000.0),
                patch(
                    "sap_cloud_sdk.agentgateway._token_cache.time.monotonic",
                    return_value=25.0,
                ),
        ):
            result = compute_expires_at(token_data, cfg)

        assert result == 395.0

    def test_uses_fallback_when_no_expiry_info(self):
        """Use config fallback TTL when no expiry metadata is available."""
        cfg = ClientConfig(fallback_token_ttl_seconds=180.0)

        with patch(
                "sap_cloud_sdk.agentgateway._token_cache.time.monotonic",
                return_value=10.0,
        ):
            result = compute_expires_at({"access_token": "opaque"}, cfg)

        assert result == 190.0

    def test_respects_jwt_exp_even_within_buffer(self):
        """Treat JWTs inside the buffer as stale instead of extending them."""
        cfg = ClientConfig(token_expiry_buffer_seconds=30.0)
        token_data = {"id_token": _make_jwt({"exp": 1020})}

        with (
                patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                      return_value=1000.0),
                patch(
                    "sap_cloud_sdk.agentgateway._token_cache.time.monotonic",
                    return_value=20.0,
                ),
        ):
            result = compute_expires_at(token_data, cfg)

        assert result == 10.0


class TestComputeExpiresAtFromBearer:
    """Tests for cache expiry resolution from a bearer auth header string."""

    def test_uses_exp_from_bearer_jwt(self):
        """Parse exp claim from Bearer JWT and apply buffer."""
        cache = _TokenCache(ClientConfig(token_expiry_buffer_seconds=20.0))
        auth_header = f"Bearer {_make_jwt({'exp': 2000})}"

        with (
                patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                      return_value=1250.0),
                patch(
                    "sap_cloud_sdk.agentgateway._token_cache.time.monotonic",
                    return_value=40.0,
                ),
        ):
            result = cache.compute_expires_at_from_bearer(auth_header)

        assert result == 770.0

    def test_falls_back_when_no_exp_in_jwt(self):
        """Use fallback TTL when JWT has no exp claim."""
        cache = _TokenCache(ClientConfig(fallback_token_ttl_seconds=300.0))
        jwt = _make_jwt({"sub": "user"})

        with patch(
                "sap_cloud_sdk.agentgateway._token_cache.time.monotonic",
                return_value=5.0,
        ):
            result = cache.compute_expires_at_from_bearer(f"Bearer {jwt}")

        assert result == 305.0

    def test_strips_bearer_prefix_case_insensitively(self):
        """Strip 'bearer ' prefix regardless of case."""
        cache = _TokenCache(
            ClientConfig(token_expiry_buffer_seconds=60,
                         fallback_token_ttl_seconds=300))
        future_exp = int(time.time()) + 600
        jwt = _make_jwt({"exp": future_exp})
        result_lower = cache.compute_expires_at_from_bearer(f"bearer {jwt}")
        result_upper = cache.compute_expires_at_from_bearer(f"Bearer {jwt}")
        assert abs(result_lower - result_upper) < 1


class TestScopeIsolation:
    """Tokens are isolated by scope key and user JWT."""

    def test_system_tokens_isolated_by_scope_key(self):
        cache = _TokenCache(ClientConfig())
        expires_at = time.monotonic() + 600

        cache.set_system_token("token-a", expires_at, "scope-a")
        cache.set_system_token("token-b", expires_at, "scope-b")

        assert cache.get_system_token("scope-a") == "token-a"
        assert cache.get_system_token("scope-b") == "token-b"

    def test_user_tokens_isolated_by_scope_key(self):
        cache = _TokenCache(ClientConfig())
        expires_at = time.monotonic() + 600

        cache.set_user_token("user-jwt", "token-a", expires_at, "scope-a")
        cache.set_user_token("user-jwt", "token-b", expires_at, "scope-b")

        assert cache.get_user_token("user-jwt", "scope-a") == "token-a"
        assert cache.get_user_token("user-jwt", "scope-b") == "token-b"

    def test_invalidate_system_token_does_not_affect_other_scopes(self):
        cache = _TokenCache(ClientConfig())
        expires_at = time.monotonic() + 600

        cache.set_system_token("token-a", expires_at, "scope-a")
        cache.set_system_token("token-b", expires_at, "scope-b")
        cache.invalidate_system_token("scope-a")

        assert cache.get_system_token("scope-a") is None
        assert cache.get_system_token("scope-b") == "token-b"

    def test_invalidate_user_token_does_not_affect_other_scopes(self):
        cache = _TokenCache(ClientConfig())
        expires_at = time.monotonic() + 600

        cache.set_user_token("user-jwt", "token-a", expires_at, "scope-a")
        cache.set_user_token("user-jwt", "token-b", expires_at, "scope-b")
        cache.invalidate_user_token("user-jwt", "scope-a")

        assert cache.get_user_token("user-jwt", "scope-a") is None
        assert cache.get_user_token("user-jwt", "scope-b") == "token-b"


class TestLruEviction:
    """LRU eviction respects max cache size and evicts least-recently-used entry."""

    def test_system_token_evicts_lru_when_full(self):
        cfg = ClientConfig(max_system_token_cache_size=2)
        cache = _TokenCache(cfg)
        expires_at = time.monotonic() + 600

        cache.set_system_token("token-a", expires_at, "scope-a")
        cache.set_system_token("token-b", expires_at, "scope-b")
        # Access scope-a so scope-b becomes LRU
        cache.get_system_token("scope-a")
        # Adding a third entry should evict scope-b (LRU)
        cache.set_system_token("token-c", expires_at, "scope-c")

        assert cache.get_system_token("scope-b") is None
        assert cache.get_system_token("scope-a") == "token-a"
        assert cache.get_system_token("scope-c") == "token-c"

    def test_user_token_evicts_lru_when_full(self):
        cfg = ClientConfig(max_user_token_cache_size=2)
        cache = _TokenCache(cfg)
        expires_at = time.monotonic() + 600

        cache.set_user_token("jwt-a", "token-a", expires_at, "scope")
        cache.set_user_token("jwt-b", "token-b", expires_at, "scope")
        # Access jwt-a so jwt-b becomes LRU
        cache.get_user_token("jwt-a", "scope")
        # Adding a third entry should evict jwt-b (LRU)
        cache.set_user_token("jwt-c", "token-c", expires_at, "scope")

        assert cache.get_user_token("jwt-b", "scope") is None
        assert cache.get_user_token("jwt-a", "scope") == "token-a"
        assert cache.get_user_token("jwt-c", "scope") == "token-c"

    def test_system_token_never_exceeds_max_size(self):
        max_size = 5
        cfg = ClientConfig(max_system_token_cache_size=max_size)
        cache = _TokenCache(cfg)
        expires_at = time.monotonic() + 600

        for i in range(max_size + 3):
            cache.set_system_token(f"token-{i}", expires_at, f"scope-{i}")

        assert len(cache._system_tokens) == max_size

    def test_user_token_never_exceeds_max_size(self):
        max_size = 4
        cfg = ClientConfig(max_user_token_cache_size=max_size)
        cache = _TokenCache(cfg)
        expires_at = time.monotonic() + 600

        for i in range(max_size + 3):
            cache.set_user_token(f"jwt-{i}", f"token-{i}", expires_at, "scope")

        assert len(cache._user_tokens) == max_size


class TestExpiredTokenEviction:
    """Expired tokens are removed from the cache on get."""

    def test_get_system_token_removes_expired_entry(self):
        cache = _TokenCache(ClientConfig())
        cache.set_system_token("stale-token", time.monotonic() - 1, "scope-x")

        result = cache.get_system_token("scope-x")

        assert result is None
        assert "scope-x" not in cache._system_tokens

    def test_get_user_token_removes_expired_entry(self):
        cache = _TokenCache(ClientConfig())
        cache.set_user_token("user-jwt", "stale-token", time.monotonic() - 1, "scope-x")

        result = cache.get_user_token("user-jwt", "scope-x")

        assert result is None
        assert len(cache._user_tokens) == 0
