"""Configuration for Agent Gateway client."""

from dataclasses import dataclass


@dataclass
class ClientConfig:
    """Configuration options for the Agent Gateway client.

    Attributes:
        timeout: HTTP timeout in seconds for token requests and MCP server calls.
            Defaults to 60 seconds.
    """

    timeout: float = 60.0
