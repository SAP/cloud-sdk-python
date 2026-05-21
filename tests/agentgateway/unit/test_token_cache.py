"""Unit tests for token cache helpers with non-trivial logic.

Cache class behavior is tested through AgentGatewayClient (test_agw_client.py)
to keep coverage focused on observable functionality. Only `_parse_jwt_exp`
and `compute_expires_at` are exercised here directly because they contain
parsing/branching logic that is hard to drive through the public API.
"""

import base64
import json
import time

from sap_cloud_sdk.agentgateway._token_cache import (
    _parse_jwt_exp,
    compute_expires_at,
)
from sap_cloud_sdk.agentgateway.config import ClientConfig


def _make_jwt(claims: dict) -> str:
    """Build a non-signed JWT for testing (header.payload.signature)."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
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
        """Return None for strings that are not three-part JWTs."""
        assert _parse_jwt_exp("not-a-jwt") is None
        assert _parse_jwt_exp("") is None
        assert _parse_jwt_exp("only.two") is None

    def test_returns_none_for_garbage_payload(self):
        """Return None when the payload segment is not valid base64/JSON."""
        assert _parse_jwt_exp("aaa.@@not-base64@@.bbb") is None


class TestComputeExpiresAt:
    """Tests for cache expiry resolution from token responses."""

    def test_uses_expires_in_when_present(self):
        """Prefer `expires_in` from the response and subtract the buffer."""
        cfg = ClientConfig(token_expiry_buffer_seconds=60, fallback_token_ttl_seconds=300)
        before = time.monotonic()
        result = compute_expires_at({"expires_in": 3600}, cfg)
        assert before + 3540 - 1 <= result <= before + 3540 + 1

    def test_expires_in_equal_to_buffer_expires_immediately(self):
        """Token whose `expires_in` equals the buffer is treated as already expiring now."""
        cfg = ClientConfig(token_expiry_buffer_seconds=60, fallback_token_ttl_seconds=300)
        before = time.monotonic()
        result = compute_expires_at({"expires_in": 60}, cfg)
        after = time.monotonic()
        assert before - 1 <= result <= after + 1

    def test_expires_in_below_buffer_is_already_stale(self):
        """Token whose `expires_in` is below the buffer resolves to a past timestamp."""
        cfg = ClientConfig(token_expiry_buffer_seconds=60, fallback_token_ttl_seconds=300)
        before = time.monotonic()
        result = compute_expires_at({"expires_in": 30}, cfg)
        assert before - 31 <= result <= before - 29

    def test_falls_back_to_id_token_exp(self):
        """Fall back to the `exp` claim of `id_token` when `expires_in` is absent."""
        cfg = ClientConfig(token_expiry_buffer_seconds=60, fallback_token_ttl_seconds=300)
        future_exp = int(time.time()) + 600
        jwt = _make_jwt({"exp": future_exp})
        before = time.monotonic()
        result = compute_expires_at({"id_token": jwt}, cfg)
        assert before + 540 - 5 <= result <= before + 540 + 5

    def test_uses_fallback_when_no_expiry_info(self):
        """Use config fallback TTL when neither `expires_in` nor `id_token` is present."""
        cfg = ClientConfig(token_expiry_buffer_seconds=60, fallback_token_ttl_seconds=300)
        before = time.monotonic()
        result = compute_expires_at({"access_token": "opaque"}, cfg)
        assert before + 300 - 1 <= result <= before + 300 + 1

    def test_uses_fallback_when_id_token_malformed(self):
        """Use fallback TTL when the `id_token` cannot be parsed."""
        cfg = ClientConfig(token_expiry_buffer_seconds=60, fallback_token_ttl_seconds=300)
        before = time.monotonic()
        result = compute_expires_at({"id_token": "garbage"}, cfg)
        assert before + 300 - 1 <= result <= before + 300 + 1

    def test_uses_fallback_when_id_token_exp_within_buffer(self):
        """Skip the `id_token` path when remaining lifetime is below the buffer."""
        # If remaining time is below the buffer, the id_token path is skipped.
        cfg = ClientConfig(token_expiry_buffer_seconds=60, fallback_token_ttl_seconds=300)
        soon_exp = int(time.time()) + 30
        jwt = _make_jwt({"exp": soon_exp})
        before = time.monotonic()
        result = compute_expires_at({"id_token": jwt}, cfg)
        assert before + 300 - 1 <= result <= before + 300 + 1

    def test_handles_invalid_expires_in_value(self):
        """Use fallback TTL when `expires_in` is not coercible to int."""
        cfg = ClientConfig(token_expiry_buffer_seconds=60, fallback_token_ttl_seconds=300)
        before = time.monotonic()
        result = compute_expires_at({"expires_in": "not-a-number"}, cfg)
        assert before + 300 - 1 <= result <= before + 300 + 1
