"""Token cache for Agent Gateway customer flow.

Caches IAS tokens (system + user-exchanged) per client to avoid redundant
mTLS token requests during agentic loops. LoB flow uses BTP Destination
Service which has its own caching, so this module only serves the customer
flow.

Keying:
- System tokens are keyed by `client_id` (or "_default" when unset).
- User tokens are keyed by `sha256(user_jwt + "|" + (client_id or ""))[:16]`.

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


def compute_expires_at(token_data: dict, config: ClientConfig) -> float:
    """Resolve the cache expiry timestamp (monotonic) for a token response.

    Resolution order:
      1. `expires_in` from the response, minus the buffer.
      2. `exp` claim from `id_token` (translated from wall clock to monotonic),
         minus the buffer.
      3. Config-provided fallback TTL.
    """
    now_mono = time.monotonic()
    buffer = config.token_expiry_buffer_seconds

    expires_in = token_data.get("expires_in")
    if expires_in is not None:
        try:
            return now_mono + int(expires_in) - buffer
        except (ValueError, TypeError):
            pass

    id_token = token_data.get("id_token")
    if id_token:
        exp = _parse_jwt_exp(id_token)
        if exp is not None:
            remaining = exp - time.time()
            if remaining > buffer:
                return now_mono + remaining - buffer

    return now_mono + config.fallback_token_ttl_seconds


class _TokenCache:
    """Per-client token cache with TTL and LRU eviction.

    Both system and user tokens use OrderedDict for LRU ordering.
    """

    _SYSTEM_DEFAULT_KEY = "_default"

    def __init__(self, config: ClientConfig):
        """Initialize empty caches bounded by sizes from `config`."""
        self._config = config
        self._system_tokens: OrderedDict[str, _CachedToken] = OrderedDict()
        self._user_tokens: OrderedDict[str, _CachedToken] = OrderedDict()

    # --- System Token ---

    def get_system_token(self, client_id: str) -> str | None:
        """Return a valid cached system token for `client_id`, or None on miss/expiry."""
        key = client_id
        cached = self._system_tokens.get(key)
        if cached and cached.is_valid():
            self._system_tokens.move_to_end(key)
            return cached.token
        if cached:
            del self._system_tokens[key]
        return None

    def set_system_token(self, token: str, expires_at: float,
                         client_id: str) -> None:
        """Cache a system token under `client_id`; evict LRU once size exceeds limit."""
        key = client_id
        self._system_tokens[key] = _CachedToken(token=token,
                                                expires_at=expires_at)
        self._system_tokens.move_to_end(key)
        while len(self._system_tokens
                  ) > self._config.max_system_token_cache_size:
            evicted, _ = self._system_tokens.popitem(last=False)
            logger.debug("System token cache full — evicted '%s'", evicted)

    def invalidate_system_token(self, client_id: str) -> None:
        """Drop the cached system token for `client_id` (no-op if absent)."""
        key = client_id
        if self._system_tokens.pop(key, None):
            logger.debug("Invalidated system token (client_id=%s)", client_id)

    # --- User Tokens ---

    def get_user_token(self, user_jwt: str, client_id: str) -> str | None:
        """Return a valid cached exchanged token for `(user_jwt, client_id)`, or None."""
        key = self._hash_key(user_jwt, client_id)
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
        client_id: str,
    ) -> None:
        """Cache an exchanged user token; evict LRU once size exceeds limit."""
        key = self._hash_key(user_jwt, client_id)
        self._user_tokens[key] = _CachedToken(token=token,
                                              expires_at=expires_at)
        self._user_tokens.move_to_end(key)
        while len(self._user_tokens) > self._config.max_user_token_cache_size:
            evicted, _ = self._user_tokens.popitem(last=False)
            logger.debug("User token cache full — evicted '%s'", evicted)

    def invalidate_user_token(self, user_jwt: str, client_id: str) -> None:
        """Drop the cached user token for `(user_jwt, client_id)` (no-op if absent)."""
        key = self._hash_key(user_jwt, client_id)
        if self._user_tokens.pop(key, None):
            logger.debug("Invalidated user token (client_id=%s)", client_id)

    # --- Maintenance ---

    def clear(self) -> None:
        """Drop all cached tokens. Forces a fresh fetch on next access."""
        self._system_tokens.clear()
        self._user_tokens.clear()

    @staticmethod
    def _hash_key(user_jwt: str, client_id: str) -> str:
        """Derive a short, stable cache key from `(user_jwt, client_id)` via sha256."""
        material = f"{user_jwt}|{client_id}"
        return hashlib.sha256(material.encode()).hexdigest()[:16]
