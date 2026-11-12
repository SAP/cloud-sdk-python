"""Token-cache helpers for Agent Gateway flows.

TTL computation for system and user tokens; a small LRU cache for gateway URLs.
Token storage is delegated to the shared Core Cache module (Cache), which
provides the kill switch, process-wide shared backend, and thread-safe LRU.

Keying:
- System tokens: `credentials.client_id` (customer) or `tenant_subdomain` (LoB).
- User tokens:   `user_cache_key(user_jwt, scope)`.

TTL helpers return the *natural* TTL (no buffer). Cache.set applies its own
expiry buffer (default 30 s), so a double-subtraction is intentional to avoid.
"""

import base64
import hashlib
import json
import time
from collections import OrderedDict


def _parse_jwt_exp(jwt: str) -> int | None:
    """Extract `exp` claim (seconds since epoch) from a JWT without verification.

    Returns None if the JWT is malformed or has no `exp` claim. The result
    is used only as a hint for cache TTL -- never for security decisions.
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
    from datetime import datetime, timezone

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


def compute_ttl_seconds(token_data: dict, fallback_ttl: float) -> int:
    """Natural TTL in seconds, NO buffer.

    Resolution order:
      expires_at - now -> expires_in -> access_token exp - now
      -> id_token exp - now -> fallback_ttl. Clamped to >= 1.
    """
    now = time.time()

    expires_at = _parse_response_expires_at(token_data.get("expires_at"))
    if expires_at is not None:
        return max(1, int(expires_at - now))

    expires_in = token_data.get("expires_in")
    if expires_in is not None:
        try:
            return max(1, int(float(expires_in)))
        except (ValueError, TypeError):
            pass

    for token_field in ("access_token", "id_token"):
        jwt = token_data.get(token_field)
        if not jwt:
            continue
        exp = _parse_jwt_exp(jwt)
        if exp is not None:
            return max(1, int(exp - now))

    return max(1, int(fallback_ttl))


def compute_ttl_seconds_from_bearer(auth_header: str, fallback_ttl: float) -> int:
    """Natural TTL from a Bearer header's JWT exp (NO buffer), else fallback_ttl."""
    jwt = auth_header[7:] if auth_header.lower().startswith("bearer ") else auth_header
    exp = _parse_jwt_exp(jwt)
    if exp is not None:
        return max(1, int(exp - time.time()))
    return max(1, int(fallback_ttl))


def user_cache_key(user_jwt: str, scope: str) -> str:
    """Derive a short, stable cache key from `(user_jwt, scope)` via sha256."""
    material = f"{user_jwt}|{scope}"
    return hashlib.sha256(material.encode()).hexdigest()[:16]


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
