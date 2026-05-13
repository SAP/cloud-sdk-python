"""Configuration for Agent Gateway client."""

from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 60.0


@dataclass
class ClientConfig:
    """Configuration options for the Agent Gateway client.

    Attributes:
        timeout: HTTP timeout in seconds for token requests and MCP server calls.
            Defaults to 60 seconds.
    """

    timeout: float = DEFAULT_TIMEOUT_SECONDS
