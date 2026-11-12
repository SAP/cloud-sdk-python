"""Unit tests for token cache helpers with non-trivial logic.

Cache class behavior is tested through AgentGatewayClient in other files.
Only helper logic is exercised directly here.
"""

import base64
import json
from unittest.mock import patch

from sap_cloud_sdk.agentgateway._token_cache import (
    _parse_jwt_exp,
    compute_ttl_seconds,
    compute_ttl_seconds_from_bearer,
    user_cache_key,
)


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


class TestComputeTtlSeconds:
    """Tests for natural TTL computation (no buffer) from token responses."""

    def test_prefers_response_expires_at(self):
        """Use expires_at - now before other fields; no buffer applied."""
        token_data = {
            "expires_at": "1600",
            "expires_in": 999,
            "access_token": _make_jwt({"exp": 1900}),
        }
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=1000.0):
            result = compute_ttl_seconds(token_data, fallback_ttl=300.0)
        assert result == 600

    def test_uses_expires_in_when_no_expires_at(self):
        """Use expires_in directly when no expires_at is present."""
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=1000.0):
            result = compute_ttl_seconds({"expires_in": 120}, fallback_ttl=300.0)
        assert result == 120

    def test_falls_back_to_access_token_exp(self):
        """Use access_token exp - now before id_token or fallback."""
        token_data = {
            "access_token": _make_jwt({"exp": 1500}),
            "id_token": _make_jwt({"exp": 1700}),
        }
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=1000.0):
            result = compute_ttl_seconds(token_data, fallback_ttl=300.0)
        assert result == 500

    def test_falls_back_to_id_token_exp(self):
        """Use id_token exp when the access token is opaque."""
        token_data = {
            "access_token": "opaque-token",
            "id_token": _make_jwt({"exp": 1400}),
        }
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=1000.0):
            result = compute_ttl_seconds(token_data, fallback_ttl=300.0)
        assert result == 400

    def test_uses_fallback_when_no_expiry_info(self):
        """Use fallback_ttl when no expiry metadata is present."""
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=1000.0):
            result = compute_ttl_seconds({"access_token": "opaque"}, fallback_ttl=300.0)
        assert result == 300

    def test_clamps_to_one_on_already_expired(self):
        """Clamp result to 1 when computed TTL would be zero or negative."""
        token_data = {"expires_at": "999"}
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=1000.0):
            result = compute_ttl_seconds(token_data, fallback_ttl=300.0)
        assert result == 1

    def test_no_buffer_applied(self):
        """No buffer is subtracted -- Cache.set owns the buffer."""
        token_data = {"expires_in": 60}
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=0.0):
            result = compute_ttl_seconds(token_data, fallback_ttl=300.0)
        # Raw 60 s, not 60 - 30 = 30
        assert result == 60


class TestComputeTtlSecondsFromBearer:
    """Tests for natural TTL from a Bearer auth header string."""

    def test_uses_exp_from_bearer_jwt(self):
        """Parse exp from Bearer JWT and return raw TTL (no buffer)."""
        auth_header = f"Bearer {_make_jwt({'exp': 2000})}"
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=1250.0):
            result = compute_ttl_seconds_from_bearer(auth_header, fallback_ttl=300.0)
        assert result == 750

    def test_falls_back_when_no_exp(self):
        """Use fallback_ttl when JWT has no exp claim."""
        jwt = _make_jwt({"sub": "user"})
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=0.0):
            result = compute_ttl_seconds_from_bearer(
                f"Bearer {jwt}", fallback_ttl=300.0
            )
        assert result == 300

    def test_strips_bearer_prefix_case_insensitively(self):
        """Strip 'bearer ' prefix regardless of case."""
        future_exp = 9_999_999_999
        jwt = _make_jwt({"exp": future_exp})
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=0.0):
            lower = compute_ttl_seconds_from_bearer(f"bearer {jwt}", fallback_ttl=300.0)
            upper = compute_ttl_seconds_from_bearer(f"Bearer {jwt}", fallback_ttl=300.0)
        assert lower == upper

    def test_no_buffer_applied(self):
        """No buffer is subtracted -- raw TTL is returned."""
        auth_header = f"Bearer {_make_jwt({'exp': 1060})}"
        with patch("sap_cloud_sdk.agentgateway._token_cache.time.time",
                   return_value=1000.0):
            result = compute_ttl_seconds_from_bearer(auth_header, fallback_ttl=300.0)
        # Raw 60 s, not 60 - 30 = 30
        assert result == 60


class TestUserCacheKey:
    """Tests for the (user_jwt, scope) cache-key derivation."""

    def test_stable_for_same_inputs(self):
        """Same jwt + scope always produces the same key."""
        k1 = user_cache_key("jwt-abc", "client-1")
        k2 = user_cache_key("jwt-abc", "client-1")
        assert k1 == k2

    def test_differs_on_scope(self):
        """Different scope produces a different key."""
        k1 = user_cache_key("jwt-abc", "client-1")
        k2 = user_cache_key("jwt-abc", "client-2")
        assert k1 != k2

    def test_differs_on_user_jwt(self):
        """Different user_jwt produces a different key."""
        k1 = user_cache_key("jwt-alice", "client-1")
        k2 = user_cache_key("jwt-bob", "client-1")
        assert k1 != k2

    def test_returns_16_char_hex_string(self):
        """Key is a 16-character lowercase hex string."""
        key = user_cache_key("any-jwt", "any-scope")
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)
