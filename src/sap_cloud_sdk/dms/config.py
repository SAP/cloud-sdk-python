import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from sap_cloud_sdk.core.secret_resolver.resolver import (
    read_from_mount_and_fallback_to_env_var,
)
from sap_cloud_sdk.destination.exceptions import ConfigError
from sap_cloud_sdk.dms.model import DMSCredentials


@dataclass
class BindingData:
    """Dataclass for DMS binding data with URI and UAA credentials.

    Attributes:
        uri: The URI endpoint for the DMS service
        uaa: JSON string containing XSUAA authentication credentials
    """

    instance_name: str
    uri: str
    uaa: str

    def validate(self) -> None:
        """Validate the binding data.

        Validates that:
        - uri is a valid URI
        - uaa is valid JSON and contains required credential fields

        Raises:
            ValueError: If uri is not a valid URI
            json.JSONDecodeError: If uaa is not valid JSON
            ValueError: If uaa JSON is missing required fields
        """
        self._validate_uri()
        self._validate_uaa()

    def _validate_uri(self) -> None:
        """Validate that uri is a valid URI.

        Raises:
            ValueError: If uri is not a valid URI
        """
        try:
            result = urlparse(self.uri)
            if not result.scheme or not result.netloc:
                raise ValueError(
                    f"Invalid URI format: '{self.uri}'. "
                    "URI must have a scheme (e.g., https://) and network location."
                )
        except Exception as e:
            raise ValueError(f"Failed to parse URI: {self.uri}") from e

    def _validate_uaa(self) -> None:
        """Validate that uaa is valid JSON with required credential fields.

        Raises:
            json.JSONDecodeError: If uaa is not valid JSON
            ValueError: If required fields are missing from UAA credentials
        """
        required_fields = {"clientid", "clientsecret", "url", "identityzone"}

        try:
            uaa_data: Dict[str, Any] = json.loads(self.uaa)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"UAA credentials must be valid JSON. Error: {e.msg}",
                e.doc,
                e.pos,
            ) from e

        missing_fields = required_fields - set(uaa_data.keys())
        if missing_fields:
            raise ValueError(
                f"UAA credentials missing required fields: {', '.join(sorted(missing_fields))}"
            )

    def to_credentials(self) -> DMSCredentials:
        """Convert the binding data to DMSCredentials.

        Parses the UAA JSON and constructs a DMSCredentials object with the necessary information
        for authenticating and connecting to the DMS service.

        Returns:
            DMSCredentials: The credentials extracted from the binding data
        """
        uaa_data: Dict[str, Any] = json.loads(self.uaa)
        token_url = uaa_data["url"].rstrip("/") + "/oauth/token"

        return DMSCredentials(
            instance_name=self.instance_name,
            uri=self.uri,
            client_id=uaa_data["clientid"],
            client_secret=uaa_data["clientsecret"],
            token_url=token_url,
            identityzone=uaa_data["identityzone"],
        )


def load_sdm_config_from_env_or_mount(instance: Optional[str] = None) -> DMSCredentials:
    """Load DMS configuration from mount with env fallback and normalize.

    Args:
        instance: Logical instance name; defaults to "default" if not provided.

    Returns:
        DMSCredentials

    Raises:
        ConfigError: If loading or validation fails.
    """
    inst = instance or "default"
    binding = BindingData(
        uri="", uaa="", instance_name=""
    )  # Initialize with empty values; will be populated by resolver

    try:
        # 1) Try mount at /etc/secrets/appfnd/destination/{instance}/...
        # 2) Fallback to env: CLOUD_SDK_CFG_SDM_{INSTANCE}_{FIELD_KEY}
        read_from_mount_and_fallback_to_env_var(
            base_volume_mount="/etc/secrets/appfnd",
            base_var_name="CLOUD_SDK_CFG",
            module="sdm",
            instance=inst,
            target=binding,
        )

        binding.validate()
        return binding.to_credentials()

    except Exception as e:
        # Rely on the central secret resolver to provide aggregated, generic guidance
        raise ConfigError(
            f"failed to load sdm configuration for instance='{inst}': {e}"
        )
