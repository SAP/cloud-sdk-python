"""Token cache for Agent Gateway flows.

Caches IAS tokens (system + user-exchanged) per client to avoid redundant
token requests during agentic loops. Used by both customer flow (mTLS) and
LoB flow (BTP Destination Service).

Keying:
- System tokens are keyed by a flow-specific scope key.
- User tokens are keyed by `sha256(user_jwt + "|" + scope_key)[:16]`.

Thread safety:
Token fetches run in the default `ThreadPoolExecutor` via
`loop.run_in_executor`. CPython GIL makes individual dict / OrderedDict
operations atomic, but compound check-then-set is not. Two concurrent
coroutines for the same key may both miss and both fetch; the race
produces redundant token requests, not corruption.
"""

import base64
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone

from sap_cloud_sdk.agentgateway.config import ClientConfig

logger = logging.getLogger(__name__)


@dataclass
class _CachedToken:
    """A cached token with monotonic expiry."""

    token: str
    expires_at: float  # time.monotonic() value

    def is_valid(self) -> bool:
        """Return True if the token has not yet reached its monotonic expiry."""
        return time.monotonic() < self.expires_at


def _parse_jwt_exp(jwt: str) -> int | None:
    """Extract `exp` claim (seconds since epoch) from a JWT without verification.

    Returns None if the JWT is malformed or has no `exp` claim. The result
    is used only as a hint for cache TTL — never for security decisions.
    """
    try:
        parts = jwt.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = claims.get("exp")
        return int(exp) if exp is not None else None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _parse_response_expires_at(expires_at: object) -> float | None:
    """Parse a token response `expires_at` value into epoch seconds."""
    if expires_at is None or isinstance(expires_at, bool):
        return None

    if isinstance(expires_at, (int, float)):
        return float(expires_at)

    if not isinstance(expires_at, str):
        return None

    normalized = expires_at.strip()
    if not normalized:
        return None

    try:
        return float(normalized)
    except ValueError:
        pass

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.timestamp()


def _monotonic_expiry_from_epoch(expiry_epoch_seconds: float, buffer: float) -> float:
    """Translate a wall-clock expiry into a monotonic deadline."""
    return time.monotonic() + (expiry_epoch_seconds - time.time()) - buffer


def _monotonic_expiry_from_ttl(ttl_seconds: float, buffer: float) -> float:
    """Translate a TTL into a monotonic deadline."""
    return time.monotonic() + ttl_seconds - buffer


def compute_expires_at(token_data: dict, config: ClientConfig) -> float:
    """Resolve the cache expiry timestamp (monotonic) for a token response.

    Resolution order:
    1. `expires_at` from the response, minus the buffer.
    2. `expires_in` from the response, minus the buffer.
    3. `exp` claim from `access_token`, minus the buffer.
    4. `exp` claim from `id_token`, minus the buffer.
    5. Config-provided fallback TTL.
    """
    buffer = config.token_expiry_buffer_seconds

    expires_at = _parse_response_expires_at(token_data.get("expires_at"))
    if expires_at is not None:
        return _monotonic_expiry_from_epoch(expires_at, buffer)

    expires_in = token_data.get("expires_in")
    if expires_in is not None:
        try:
            return _monotonic_expiry_from_ttl(float(expires_in), buffer)
        except (ValueError, TypeError):
            pass

    for token_field in ("access_token", "id_token"):
        jwt = token_data.get(token_field)
        if not jwt:
            continue

        exp = _parse_jwt_exp(jwt)
        if exp is not None:
            return _monotonic_expiry_from_epoch(float(exp), buffer)

    return time.monotonic() + config.fallback_token_ttl_seconds


class _GatewayUrlCache:
    """LRU-bounded cache for gateway URLs keyed by scope key.

    URLs are assumed stable for the lifetime of a client instance. Bounded to
    avoid unbounded growth in long-lived clients serving many tenants.
    """

    def __init__(self, max_size: int = 64):
        self._max_size = max_size
        self._cache: OrderedDict[str, str] = OrderedDict()

    def get(self, scope_key: str) -> str | None:
        value = self._cache.get(scope_key)
        if value is not None:
            self._cache.move_to_end(scope_key)
        return value

    def __setitem__(self, scope_key: str, url: str) -> None:
        self._cache[scope_key] = url
        self._cache.move_to_end(scope_key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)


class _TokenCache:
    """Per-client token cache with TTL and LRU eviction.

    Both system and user tokens use OrderedDict for LRU ordering.
    """

    def __init__(self, config: ClientConfig):
        """Initialize empty caches bounded by sizes from `config`."""
        self._config = config
        self._system_tokens: OrderedDict[str, _CachedToken] = OrderedDict()
        self._user_tokens: OrderedDict[str, _CachedToken] = OrderedDict()

    # --- System Token ---

    def get_system_token(self, scope_key: str) -> str | None:
        """Return a valid cached system token for `scope_key`, or None."""
        cached = self._system_tokens.get(scope_key)
        if cached and cached.is_valid():
            self._system_tokens.move_to_end(scope_key)
            return cached.token
        if cached:
            del self._system_tokens[scope_key]
        return None

    def set_system_token(self, token: str, expires_at: float, scope_key: str) -> None:
        """Cache a system token under `scope_key`; evict LRU once size exceeds limit."""
        self._system_tokens[scope_key] = _CachedToken(
            token=token, expires_at=expires_at
        )
        self._system_tokens.move_to_end(scope_key)
        while len(self._system_tokens) > self._config.max_system_token_cache_size:
            evicted, _ = self._system_tokens.popitem(last=False)
            logger.debug("System token cache full — evicted '%s'", evicted)

    def invalidate_system_token(self, scope_key: str) -> None:
        """Drop the cached system token for `scope_key` (no-op if absent)."""
        if self._system_tokens.pop(scope_key, None):
            logger.debug("Invalidated system token (scope_key=%s)", scope_key)

    # --- User Tokens ---

    def get_user_token(self, user_jwt: str, scope_key: str) -> str | None:
        """Return a valid cached exchanged token for `(user_jwt, scope_key)`, or None."""
        key = self._hash_key(user_jwt, scope_key)
        cached = self._user_tokens.get(key)
        if cached and cached.is_valid():
            self._user_tokens.move_to_end(key)
            return cached.token
        if cached:
            del self._user_tokens[key]
        return None

    def set_user_token(
        self,
        user_jwt: str,
        token: str,
        expires_at: float,
        scope_key: str,
    ) -> None:
        """Cache an exchanged user token; evict LRU once size exceeds limit."""
        key = self._hash_key(user_jwt, scope_key)
        self._user_tokens[key] = _CachedToken(token=token, expires_at=expires_at)
        self._user_tokens.move_to_end(key)
        while len(self._user_tokens) > self._config.max_user_token_cache_size:
            evicted, _ = self._user_tokens.popitem(last=False)
            logger.debug("User token cache full — evicted '%s'", evicted)

    def invalidate_user_token(self, user_jwt: str, scope_key: str) -> None:
        """Drop the cached user token for `(user_jwt, scope_key)` (no-op if absent)."""
        key = self._hash_key(user_jwt, scope_key)
        if self._user_tokens.pop(key, None):
            logger.debug("Invalidated user token (scope_key=%s)", scope_key)

    # --- Utility ---

    def compute_expires_at(self, token_data: dict) -> float:
        """Resolve the cache expiry timestamp (monotonic) for a token response."""
        return compute_expires_at(token_data, self._config)

    def compute_expires_at_from_bearer(self, auth_header: str) -> float:
        """Resolve the cache expiry timestamp for a bearer auth header string.

        Strips the 'Bearer ' prefix and parses the `exp` claim from the JWT.
        Falls back to the config-provided fallback TTL if parsing fails.
        """
        buffer = self._config.token_expiry_buffer_seconds

        jwt = (
            auth_header[7:]
            if auth_header.lower().startswith("bearer ")
            else auth_header
        )
        exp = _parse_jwt_exp(jwt)
        if exp is not None:
            return _monotonic_expiry_from_epoch(float(exp), buffer)

        return time.monotonic() + self._config.fallback_token_ttl_seconds

    # --- Maintenance ---

    def clear(self) -> None:
        """Drop all cached tokens. Forces a fresh fetch on next access."""
        self._system_tokens.clear()
        self._user_tokens.clear()

    @staticmethod
    def _hash_key(user_jwt: str, scope_key: str) -> str:
        """Derive a short, stable cache key from `(user_jwt, scope_key)` via sha256."""
        material = f"{user_jwt}|{scope_key}"
        return hashlib.sha256(material.encode()).hexdigest()[:16]
