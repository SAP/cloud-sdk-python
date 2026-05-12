"""Configuration and secret resolution for the Agent Memory service.

Loads service binding secrets from a mounted volume with environment fallback,
then normalises into an ``AgentMemoryConfig``.

Mount path convention::



    /etc/secrets/appfnd/hana-agent-memory/default/{field_key}

Keys: ``application_url``, ``uaa.url``, ``uaa.clientid``, ``uaa.clientsecret``

Env fallback convention (uppercased)::

    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA_URL
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA_CLIENTID
    CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA_CLIENTSECRET
"""

from dataclasses import dataclass, field
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


# NOTE: BindingData must NOT use `from __future__ import annotations`
# because the secret resolver checks `f.type is str` at runtime, which requires
# actual type objects rather than string annotations.


@dataclass
class BindingData:
    """Raw binding secrets read by the secret resolver.

    All fields must be plain ``str`` to satisfy the resolver contract.
    """

    application_url: str = ""
    uaa_url: str = field(default="", metadata={"secret": "uaa.url"})
    uaa_clientid: str = field(default="", metadata={"secret": "uaa.clientid"})
    uaa_clientsecret: str = field(default="", metadata={"secret": "uaa.clientsecret"})

    def validate(self) -> None:
        """Raise ``AgentMemoryConfigError`` if any required field is empty."""
        missing = [
            f
            for f in ("application_url", "uaa_url", "uaa_clientid", "uaa_clientsecret")
            if not getattr(self, f)
        ]
        if missing:
            raise AgentMemoryConfigError(
                f"Agent Memory binding is missing required fields: {', '.join(missing)}"
            )

    def extract_config(self) -> AgentMemoryConfig:
        """Derive an ``AgentMemoryConfig`` from the raw binding fields."""
        return AgentMemoryConfig(
            base_url=self.application_url,
            token_url=self.uaa_url.rstrip("/") + "/oauth/token",
            client_id=self.uaa_clientid,
            client_secret=self.uaa_clientsecret,
        )


_ENV_PREFIX = "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT"

# Explicit env var names — dots are not valid in shell variable names,
# so we define these directly rather than deriving them from BindingData metadata keys
# (which use dots to match the BTP mount-path file naming convention).
_ENV_VARS = {
    "application_url": f"{_ENV_PREFIX}_APPLICATION_URL",
    "uaa_url": f"{_ENV_PREFIX}_UAA_URL",
    "uaa_clientid": f"{_ENV_PREFIX}_UAA_CLIENTID",
    "uaa_clientsecret": f"{_ENV_PREFIX}_UAA_CLIENTSECRET",
}


def _load_binding_from_env() -> BindingData:
    """Read Agent Memory binding from environment variables.

    Raises:
        AgentMemoryConfigError: If any required variable is absent.
    """
    import os

    binding = BindingData()
    missing: list[str] = []
    for attr, var in _ENV_VARS.items():
        value = os.environ.get(var)
        if not value:
            missing.append(var)
        else:
            setattr(binding, attr, value)
    if missing:
        raise AgentMemoryConfigError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    return binding


def _load_config_from_env() -> AgentMemoryConfig:
    """Load Agent Memory configuration from a mounted volume or environment variables.

    Tries (in order):
    1. Mount at ``/etc/secrets/appfnd/hana-agent-memory/default/``
    2. Environment variables ``CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_*``

    Returns:
        A validated ``AgentMemoryConfig``.

    Raises:
        AgentMemoryConfigError: If configuration cannot be loaded or is incomplete.
    """
    from sap_cloud_sdk.core.secret_resolver.resolver import _load_from_mount

    mount_error: Exception | None = None
    try:
        binding = BindingData()
        _load_from_mount("/etc/secrets/appfnd", "hana-agent-memory", "default", binding)
        binding.validate()
        return binding.extract_config()
    except Exception as exc:
        mount_error = exc

    try:
        binding = _load_binding_from_env()
        binding.validate()
        return binding.extract_config()
    except AgentMemoryConfigError:
        raise
    except Exception as exc:
        raise AgentMemoryConfigError(
            f"Failed to load Agent Memory configuration: mount={mount_error}; env={exc}"
        ) from exc
