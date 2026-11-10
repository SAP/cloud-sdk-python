"""Configuration and secret resolution for the ADMS (Advanced Document Management Service) module.

Loads IAS service binding secrets from a mounted volume with environment fallback,
then normalises into a AdmsConfig model that the HTTP layer consumes.

Mount path convention:
  /etc/secrets/appfnd/adms/{instance}/
Keys (from ADM IAS binding — service: identity, credential-type: X509_GENERATED):
  - clientid
  - clientsecret
  - url          (IAS tenant base URL, e.g. https://{tenant}.accounts.ondemand.com)
  - uri          (ADM service base URL)

Environment variable fallback (uppercase):
  CLOUD_SDK_CFG_ADMS_{INSTANCE}_{FIELD}
  e.g. CLOUD_SDK_CFG_ADMS_DEFAULT_CLIENTID
"""

from dataclasses import dataclass

from sap_cloud_sdk.core.secret_resolver.resolver import (
    read_from_mount_and_fallback_to_env_var,
)
from sap_cloud_sdk.adms.exceptions import ConfigError

_DEFAULT_INSTANCE = "default"
_SECRET_MOUNT_BASE = "/etc/secrets/appfnd"
_ENV_VAR_BASE = "CLOUD_SDK_CFG"
_SERVICE_PATH = "/odata/v4/DocumentService"
_ADMIN_SERVICE_PATH = "/odata/v4/AdminService"
_CONFIG_SERVICE_PATH = "/odata/v4/ConfigurationService"


@dataclass
class AdmsConfig:
    """Normalised configuration for the ADMS service binding.

    Combines the IAS OAuth2 credentials with the ADMS service base URL.

    Attributes:
        service_url: ADM service base URL (e.g. https://adm.cfapps.{region}.hana.ondemand.com)
        ias_url: IAS tenant base URL used to derive the token endpoint
        client_id: IAS OAuth2 client ID
        client_secret: IAS OAuth2 client secret
        resource: Optional IAS resource URI that scopes the token to the ADM application
            (e.g. ``urn:sap:identity:application:provider:name:my-adm-app``).
            When set it is forwarded as the ``resource`` parameter in every
            ``client_credentials`` token request and IAS returns a JWT whose
            ``aud`` claim matches the ADM application, satisfying ADM's token
            validation.  Must be set when connecting to a real BTP ADM instance.
    """

    service_url: str
    ias_url: str
    client_id: str
    client_secret: str
    resource: str | None = None


@dataclass
class _BindingData:
    """Raw fields read from the mounted secret / env vars.

    All fields must be ``str`` to satisfy the secret resolver contract.
    """

    clientid: str = ""
    clientsecret: str = ""
    url: str = ""  # IAS tenant base URL
    uri: str = ""  # ADM service base URL
    resource: str = ""  # Optional IAS resource URI (app provider name)

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("clientid", self.clientid),
                ("clientsecret", self.clientsecret),
                ("url", self.url),
                ("uri", self.uri),
            )
            if not value
        ]
        if missing:
            raise ConfigError(
                f"ADMS binding is missing required fields: {', '.join(missing)}"
            )

    def to_config(self) -> AdmsConfig:
        return AdmsConfig(
            service_url=self.uri.rstrip("/"),
            ias_url=self.url.rstrip("/"),
            client_id=self.clientid,
            client_secret=self.clientsecret,
            resource=self.resource or None,
        )


def load_from_env_or_mount(instance: str | None = None) -> AdmsConfig:
    """Load ADMS configuration from a mounted secret volume or environment variables.

    Args:
        instance: Logical binding instance name.  Defaults to ``"default"``.

    Returns:
        A validated :class:`AdmsConfig` ready for use by the auth layer.

    Raises:
        ConfigError: If any required field is missing after resolution.
    """
    instance = instance or _DEFAULT_INSTANCE
    raw = _BindingData()
    try:
        read_from_mount_and_fallback_to_env_var(
            base_volume_mount=_SECRET_MOUNT_BASE,
            base_var_name=_ENV_VAR_BASE,
            module="adms",
            instance=instance,
            target=raw,
        )
    except Exception as exc:
        raise ConfigError(
            f"failed to load ADMS binding for instance '{instance}': {exc}"
        ) from exc

    raw.validate()
    return raw.to_config()
