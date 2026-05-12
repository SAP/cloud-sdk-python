"""Configuration and secret resolution for the Agent Memory service.

Loads service binding secrets from a mounted volume with environment fallback,
then normalises into an ``AgentMemoryConfig``.

Mount path convention::

    /etc/secrets/appfnd/hana-agent-memory/default/url
    /etc/secrets/appfnd/hana-agent-memory/default/uaa

``url`` is the Agent Memory service base URL (plain string).
``uaa`` is a JSON string with OAuth2 credentials containing at minimum:
``clientid``, ``clientsecret``, and ``url`` (UAA base URL).

Env fallback convention::

    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_URL
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA
"""

import json
from dataclasses import dataclass
from typing import Optional

from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryConfigError


@dataclass
class AgentMemoryConfig:
    """Configuration for the Agent Memory service.

    Attributes:
        base_url: The base URL of the Agent Memory service.
        token_url: The OAuth2 token endpoint URL. Optional — if not provided,
                   requests are sent without authentication (useful for local development).
        client_id: The OAuth2 client ID. Optional.
        client_secret: The OAuth2 client secret. Optional.
        timeout: Timeout in seconds for HTTP requests. Default is 30.0.

    Example — deployed BTP service::

        config = AgentMemoryConfig(
            base_url="https://<service-host>",
            token_url="https://<tenant>.authentication.<region>/oauth/token",
            client_id="<client-id>",
            client_secret="<client-secret>",
        )

    Example — local development (no auth)::

        config = AgentMemoryConfig(base_url="http://localhost:3000")
    """

    base_url: str
    token_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if not self.base_url:
            raise AgentMemoryConfigError("base_url must be a non-empty string")
        if self.token_url is not None and not self.token_url:
            raise AgentMemoryConfigError(
                "token_url must be a non-empty string when provided"
            )
        if self.client_id is not None and not self.client_id:
            raise AgentMemoryConfigError(
                "client_id must be a non-empty string when provided"
            )
        if self.client_secret is not None and not self.client_secret:
            raise AgentMemoryConfigError(
                "client_secret must be a non-empty string when provided"
            )


@dataclass
class BindingData:
    """Raw binding secrets read by the secret resolver.

    All fields must be plain ``str`` to satisfy the resolver contract.
    """

    url: str = ""
    uaa: str = ""

    def validate(self) -> None:
        """Raise ``AgentMemoryConfigError`` if any required field is empty."""
        if not self.url:
            raise AgentMemoryConfigError(
                "Agent Memory binding is missing required field: url"
            )
        if not self.uaa:
            raise AgentMemoryConfigError(
                "Agent Memory binding is missing required field: uaa"
            )

    def extract_config(self) -> AgentMemoryConfig:
        """Parse the UAA JSON string and return an ``AgentMemoryConfig``."""
        try:
            uaa_data = json.loads(self.uaa, strict=False)
        except json.JSONDecodeError as e:
            raise AgentMemoryConfigError(f"Failed to parse uaa JSON: {e}")

        try:
            return AgentMemoryConfig(
                base_url=self.url,
                token_url=uaa_data["url"].rstrip("/") + "/oauth/token",
                client_id=uaa_data["clientid"],
                client_secret=uaa_data["clientsecret"],
            )
        except KeyError as e:
            raise AgentMemoryConfigError(f"Missing required field in uaa JSON: {e}")


def _load_config_from_env() -> AgentMemoryConfig:
    """Load Agent Memory configuration from a mounted volume or environment variables.

    Uses the secret resolver with fallback order:
    1. Mount at ``/etc/secrets/appfnd/hana-agent-memory/default/``
    2. Environment variables ``CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_*``

    Returns:
        A validated ``AgentMemoryConfig``.

    Raises:
        AgentMemoryConfigError: If configuration cannot be loaded or is incomplete.
    """
    from sap_cloud_sdk.core.secret_resolver import (
        read_from_mount_and_fallback_to_env_var,
    )

    try:
        binding = BindingData()
        read_from_mount_and_fallback_to_env_var(
            base_volume_mount="/etc/secrets/appfnd",
            base_var_name="CLOUD_SDK_CFG",
            module="hana-agent-memory",
            instance="default",
            target=binding,
        )
        binding.validate()
        return binding.extract_config()
    except AgentMemoryConfigError:
        raise
    except Exception as exc:
        raise AgentMemoryConfigError(
            f"Failed to load Agent Memory configuration: {exc}"
        ) from exc
