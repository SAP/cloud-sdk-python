"""Configuration and secret resolution for Destination Service.

Loads service binding secrets from a mounted volume with environment fallback,
then normalizes into a unified DestinationConfig model.

Mount path convention:
  /etc/secrets/appfnd/destination/{instance}/
Keys:
  - clientid
  - clientsecret
  - url (auth server base)
  - uri (destination service base)
  - identityzone

Env fallback convention (uppercased):
  CLOUD_SDK_CFG_DESTINATION_destination_{instance}_{field_key}
  e.g., CLOUD_SDK_CFG_DESTINATION_DESTINATION_DEFAULT_CLIENTID
  CLOUD_SDK_CFG_DESTINATION_destination_{instance}_{field_key}
  e.g., CLOUD_SDK_CFG_DESTINATION_DESTINATION_DEFAULT_CLIENTID

Note: We use the common secret resolver with:
  base_volume_mount="/etc/secrets/appfnd"
  base_var_name="CLOUD_SDK_CFG"
  module="destination"
  instance="{instance}"
This results in env var names: CLOUD_SDK_CFG_DESTINATION_{INSTANCE}_{FIELD_KEY}
This results in env var names: CLOUD_SDK_CFG_DESTINATION_{INSTANCE}_{FIELD_KEY}
"""

from dataclasses import dataclass
from typing import Optional
import os

from sap_cloud_sdk.core.secret_resolver.resolver import (
    read_from_mount_and_fallback_to_env_var,
)
from sap_cloud_sdk.destination.exceptions import ConfigError
from sap_cloud_sdk.destination._models import TransparentProxy

_TRANSPARENT_PROXY_ENV_VAR = "APPFND_CONHOS_TRANSP_PROXY"
_TRANSPARENT_PROXY_ENV_VAR = "APPFND_CONHOS_TRANSP_PROXY"


@dataclass
class DestinationConfig:
    """Service binding for Destination Service.

    Combines:
      - Destination service base URL (url)
      - OAuth2 token endpoint and client credentials (token_url, client_id, client_secret)
      - Metadata from the binding (identityzone)

    This normalized binding is produced by configuration loading routines and consumed
    by the TokenProvider and DestinationHttp classes.

    Args:
        url: Destination service base URL (e.g., https://destination-configuration.cfapps.{region}.hana.ondemand.com)
        token_url: OAuth2 token endpoint (e.g., https://{provider}.authentication.{region}.hana.ondemand.com/oauth/token)
        client_id: OAuth2 client id
        client_secret: OAuth2 client secret
        identityzone: Provider identity zone, used for tenant token URL derivation
    """

    # Destination service base (formerly ServiceConfig.url)
    url: str
    # OAuth2 token endpoint and client credentials (formerly OAuthConfig)
    token_url: str
    client_id: str
    client_secret: str
    # Metadata from binding
    identityzone: str


@dataclass
class BindingData:
    """Dataclass for reading raw binding secrets via the secret resolver.

    All fields must be str to satisfy the secret resolver contract.
    """

    clientid: str = ""
    clientsecret: str = ""
    url: str = ""  # Auth server base, e.g., https://{provider}.authentication.{region}.hana.ondemand.com
    uri: str = ""  # Destination service base, e.g., https://destination-configuration.cfapps.{region}.hana.ondemand.com
    identityzone: str = ""

    def validate(self) -> None:
        """Validate that required fields are present."""
        if not self.clientid:
            raise ValueError("clientid is required")
        if not self.clientsecret:
            raise ValueError("clientsecret is required")
        # Service base URL should be provided, prefer 'uri' but allow fallback to 'url'
        if not self.uri:
            raise ValueError("uri is required")
        # Auth base URL is required to build token_url
        if not self.url:
            raise ValueError("url is required")
        # Identity zone is required for tenant token URL derivation
        if not self.identityzone:
            raise ValueError("identityzone is required")

    def to_binding(self) -> DestinationConfig:
        """Transform raw binding into a unified DestinationConfig."""
        token_url = self.url.rstrip("/") + "/oauth/token"

        return DestinationConfig(
            url=self.uri,
            token_url=token_url,
            client_id=self.clientid,
            client_secret=self.clientsecret,
            identityzone=self.identityzone,
        )


def load_from_env_or_mount(instance: Optional[str] = None) -> DestinationConfig:
    """Load Destination configuration from mount with env fallback and normalize.

    Args:
        instance: Logical instance name; defaults to "default" if not provided.

    Returns:
        DestinationConfig

    Raises:
        ConfigError: If loading or validation fails.
    """
    inst = instance or "default"
    binding = BindingData()

    try:
        # 1) Try mount at /etc/secrets/appfnd/destination/{instance}/...
        # 2) Fallback to env: CLOUD_SDK_CFG_DESTINATION_{INSTANCE}_{FIELD_KEY}
        read_from_mount_and_fallback_to_env_var(
            base_volume_mount="/etc/secrets/appfnd",
            base_var_name="CLOUD_SDK_CFG",
            module="destination",
            instance=inst,
            target=binding,
        )

        binding.validate()
        return binding.to_binding()

    except Exception as e:
        # Rely on the central secret resolver to provide aggregated, generic guidance
        raise ConfigError(
            f"failed to load destination configuration for instance='{inst}': {e}"
        )


def load_transparent_proxy() -> Optional[TransparentProxy]:
    """Load transparent proxy configuration from environment variable.
    The environment variable APPFND_CONHOS_TRANSP_PROXY should be in the format:
    The environment variable APPFND_CONHOS_TRANSP_PROXY should be in the format:
    {proxy_name}.{namespace}

    Returns:
        TransparentProxy if configured, otherwise None if not configured.
    Raises:
        ConfigError: If the environment variable format is invalid.
    """

    proxy_envvar = os.environ.get(_TRANSPARENT_PROXY_ENV_VAR)

    if not proxy_envvar:
        return None

    try:
        parts = proxy_envvar.split(".")
        proxy_name = parts[0]
        namespace = parts[1]

        if not proxy_name or not namespace:
            raise ConfigError(
                f"invalid transparent proxy format in {_TRANSPARENT_PROXY_ENV_VAR}: expected 'proxy-name.namespace', got '{proxy_envvar}'"
            )

        return TransparentProxy(proxy_name=proxy_name, namespace=namespace)
    except IndexError:
        raise ConfigError(
            f"invalid transparent proxy format in {_TRANSPARENT_PROXY_ENV_VAR}: expected 'proxy-name.namespace', got '{proxy_envvar}'"
        )
