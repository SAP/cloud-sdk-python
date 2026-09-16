"""Configuration for Agent Gateway client."""

from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_FALLBACK_TOKEN_TTL_SECONDS = 300.0
DEFAULT_TOKEN_EXPIRY_BUFFER_SECONDS = 30.0
DEFAULT_MAX_SYSTEM_TOKEN_CACHE_SIZE = 32
DEFAULT_MAX_USER_TOKEN_CACHE_SIZE = 256
DEFAULT_MAX_CONCURRENT_TASKS = 15


@dataclass
class ClientConfig:
    """Configuration options for the Agent Gateway client.

    Attributes:
        timeout: HTTP timeout in seconds for token requests and MCP server calls.
            Defaults to 60 seconds.
        fallback_token_ttl_seconds: Fallback cache TTL used when a token
            response does not provide expiry metadata.
        token_expiry_buffer_seconds: Safety buffer subtracted from explicit
            token expiries before a cached token is considered stale.
        max_system_token_cache_size: Maximum number of cached system tokens.
        max_user_token_cache_size: Maximum number of cached user tokens.
        max_concurrent_tasks: Maximum number of MCP and Agent fetches (MCP tool
            discovery or A2A agent card fetches) that run concurrently.
            Defaults to 15.
    """

    timeout: float = DEFAULT_TIMEOUT_SECONDS
    fallback_token_ttl_seconds: float = DEFAULT_FALLBACK_TOKEN_TTL_SECONDS
    token_expiry_buffer_seconds: float = DEFAULT_TOKEN_EXPIRY_BUFFER_SECONDS
    max_system_token_cache_size: int = DEFAULT_MAX_SYSTEM_TOKEN_CACHE_SIZE
    max_user_token_cache_size: int = DEFAULT_MAX_USER_TOKEN_CACHE_SIZE
    max_concurrent_tasks: int = DEFAULT_MAX_CONCURRENT_TASKS

    def __post_init__(self) -> None:
        if self.token_expiry_buffer_seconds >= self.fallback_token_ttl_seconds:
            raise ValueError(
                f"token_expiry_buffer_seconds ({self.token_expiry_buffer_seconds}) "
                f"must be less than fallback_token_ttl_seconds ({self.fallback_token_ttl_seconds})"
            )
