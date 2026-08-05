"""Configuration and secret resolution for the Agent Memory service.

Loads service binding secrets from a mounted volume with environment fallback,
then normalises into an ``AgentMemoryConfig``.

Mount path convention::

    /etc/secrets/appfnd/hana-agent-memory/default/application_url     (provider)
    /etc/secrets/appfnd/hana-agent-memory/<tenant>/application_url     (subscriber)
    /etc/secrets/appfnd/hana-agent-memory/default/uaa
    /etc/secrets/appfnd/hana-agent-memory/<tenant>/uaa

``application_url`` is the Agent Memory service base URL (plain string).
``uaa`` is a JSON string with OAuth2 credentials containing at minimum:
``clientid``, ``clientsecret``, and ``url`` (UAA base URL).

Env fallback convention::

    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_<TENANT>_APPLICATION_URL
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_<TENANT>_UAA
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
        identityzone: The provider tenant identity zone subdomain. Required when using
                      ``SUBSCRIBER`` access strategy so the subscriber token URL
                      can be derived by replacing this value in ``token_url``.
        timeout: Timeout in seconds for HTTP requests. Default is 30.0.

    Example — deployed BTP service::

        config = AgentMemoryConfig(
            base_url="https://<service-host>",
            token_url="https://<tenant>.authentication.<region>/oauth/token",
            client_id="<client-id>",
            client_secret="<client-secret>",
            identityzone="<provider-subdomain>",
        )

    Example — local development (no auth)::

        config = AgentMemoryConfig(base_url="http://localhost:3000")
    """

    base_url: str
    token_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    identityzone: Optional[str] = None
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
        if self.identityzone is not None and not self.identityzone:
            raise AgentMemoryConfigError(
                "identityzone must be a non-empty string when provided"
            )


@dataclass
class BindingData:
    """Raw binding secrets read by the secret resolver.

    All fields must be plain ``str`` to satisfy the resolver contract.
    """

    application_url: str = ""
    uaa: str = ""

    def validate(self) -> None:
        """Raise ``AgentMemoryConfigError`` if any required field is empty."""
        if not self.application_url:
            raise AgentMemoryConfigError(
                "Agent Memory binding is missing required field: application_url"
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
                base_url=self.application_url,
                token_url=uaa_data["url"].rstrip("/") + "/oauth/token",
                client_id=uaa_data["clientid"],
                client_secret=uaa_data["clientsecret"],
                identityzone=uaa_data.get("identityzone"),
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
    return _load_config_for_instance("default")


def _load_config_for_instance(instance: str) -> AgentMemoryConfig:
    """Load Agent Memory configuration for a named binding instance.

    Uses the secret resolver with fallback order:
    1. Mount at ``/etc/secrets/appfnd/hana-agent-memory/{instance}/``
    2. Environment variables ``CLOUD_SDK_CFG_HANA_AGENT_MEMORY_{INSTANCE}_*``

    This is used to load tenant-specific bindings when the runtime provisions
    a dedicated service instance per subscriber tenant.

    Args:
        instance: The binding instance name — ``"default"`` for the provider,
            or a tenant subdomain for a subscriber (e.g. ``"acme-corp"``).

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
            instance=instance,
            target=binding,
        )
        binding.validate()
        return binding.extract_config()
    except AgentMemoryConfigError:
        raise
    except Exception as exc:
        raise AgentMemoryConfigError(
            f"Failed to load Agent Memory configuration for instance '{instance}': {exc}"
        ) from exc
