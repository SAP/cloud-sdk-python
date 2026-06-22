"""Configuration and secret resolution for SAP Print Service.

Loads service binding secrets from a mounted volume with environment fallback,
then normalizes into a unified PrintConfig model.

Mount path convention:
  /etc/secrets/appfnd/print/{instance}/
Keys:
  - url   (Print service base URL, e.g. https://api.eu10.print.services.sap)
  - uaa   (JSON string with clientid, clientsecret, url, identityzone)

Env fallback convention:
  CLOUD_SDK_CFG_PRINT_{INSTANCE}_{FIELD_KEY}
  e.g., CLOUD_SDK_CFG_PRINT_DEFAULT_URL
"""

from dataclasses import dataclass
from typing import Optional
import json
import logging

from sap_cloud_sdk.core.secret_resolver.resolver import (
    read_from_mount_and_fallback_to_env_var,
)
from sap_cloud_sdk.print.exceptions import ConfigError

logger = logging.getLogger(__name__)


@dataclass
class PrintConfig:
    """Service binding for SAP Print Service.

    Args:
        url: Print service base URL (e.g., https://api.eu10.print.services.sap)
        token_url: OAuth2 token endpoint
        client_id: OAuth2 client id
        client_secret: OAuth2 client secret
    """

    url: str
    token_url: str
    client_id: str
    client_secret: str


@dataclass
class _BindingData:
    """Raw binding secrets read via the secret resolver."""

    url: str = ""
    uaa: str = ""  # JSON string: {clientid, clientsecret, url, identityzone}

    def validate(self) -> None:
        if not self.url:
            raise ValueError("url is required")
        if not self.uaa:
            raise ValueError("uaa is required")

    def to_config(self) -> PrintConfig:
        try:
            uaa = json.loads(self.uaa)
        except json.JSONDecodeError as e:
            raise ValueError(f"uaa is not valid JSON: {e}") from e

        client_id = uaa.get("clientid", "")
        client_secret = uaa.get("clientsecret", "")
        auth_url = uaa.get("url", "")

        if not client_id:
            raise ValueError("uaa.clientid is required")
        if not client_secret:
            raise ValueError("uaa.clientsecret is required")
        if not auth_url:
            raise ValueError("uaa.url is required")

        token_url = auth_url.rstrip("/") + "/oauth/token"

        return PrintConfig(
            url=self.url,
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
        )


def load_from_env_or_mount(instance: Optional[str] = None) -> PrintConfig:
    """Load Print configuration from mount with env fallback and normalize.

    Args:
        instance: Logical instance name; defaults to "default" if not provided.

    Returns:
        PrintConfig

    Raises:
        ConfigError: If loading or validation fails.
    """
    inst = instance or "default"
    binding = _BindingData()

    try:
        read_from_mount_and_fallback_to_env_var(
            base_volume_mount="/etc/secrets/appfnd",
            base_var_name="CLOUD_SDK_CFG",
            module="print",
            instance=inst,
            target=binding,
        )

        binding.validate()
        return binding.to_config()

    except Exception as e:
        logger.error(
            "failed to load print configuration for instance='%s': %s", inst, e
        )
        raise ConfigError(
            f"failed to load print configuration for instance='{inst}': {e}"
        ) from e
