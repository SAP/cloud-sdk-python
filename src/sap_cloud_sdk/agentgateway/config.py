"""Configuration for Agent Gateway client."""

from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_TOKEN_EXPIRY_BUFFER_SECONDS = 60
DEFAULT_MAX_USER_TOKEN_CACHE_SIZE = 10
DEFAULT_MAX_SYSTEM_TOKEN_CACHE_SIZE = 10
DEFAULT_FALLBACK_TOKEN_TTL_SECONDS = 300


@dataclass
class ClientConfig:
    """Configuration options for the Agent Gateway client.

    Attributes:
        timeout: HTTP timeout in seconds for token requests and MCP server calls.
            Defaults to 60 seconds.
        token_expiry_buffer_seconds: Refresh tokens this many seconds before
            their reported expiry. Defaults to 60 seconds.
        max_user_token_cache_size: Maximum number of user tokens cached
            per client. LRU eviction once exceeded. Defaults to 10.
        max_system_token_cache_size: Maximum number of system tokens cached
            per client (one per app_tid). LRU eviction once exceeded.
            Defaults to 10.
        fallback_token_ttl_seconds: TTL applied when neither `expires_in`
            nor a parseable `id_token` exp claim is available in the token
            response. Defaults to 300 seconds.
    """

    timeout: float = DEFAULT_TIMEOUT_SECONDS
    token_expiry_buffer_seconds: int = DEFAULT_TOKEN_EXPIRY_BUFFER_SECONDS
    max_user_token_cache_size: int = DEFAULT_MAX_USER_TOKEN_CACHE_SIZE
    max_system_token_cache_size: int = DEFAULT_MAX_SYSTEM_TOKEN_CACHE_SIZE
    fallback_token_ttl_seconds: int = DEFAULT_FALLBACK_TOKEN_TTL_SECONDS
