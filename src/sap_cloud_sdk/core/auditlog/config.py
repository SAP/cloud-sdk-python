"""Configuration parsing for SAP Audit Log Service.

This module handles parsing of audit log configuration from SAP Cloud Platform
service bindings where OAuth2 credentials are embedded as JSON strings.
"""

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sap_cloud_sdk.core.auditlog.exceptions import ClientCreationError

if TYPE_CHECKING:
    from sap_cloud_sdk.core.secret_resolver import ConfigFactory


@dataclass
class AuditLogConfig:
    """Audit Log configuration.

    This is the main configuration class.
    """

    client_id: str
    client_secret: str
    oauth_url: str
    service_url: str

    def __post_init__(self) -> None:
        """Validate that all required fields are set."""
        if not self.client_id:
            raise ValueError("client_id is required")
        if not self.client_secret:
            raise ValueError("client_secret is required")
        if not self.oauth_url:
            raise ValueError("oauth_url is required")
        if not self.service_url:
            raise ValueError("service_url is required")

    @property
    def token_url(self) -> str:
        """OAuth2 token endpoint derived from oauth_url."""
        return self.oauth_url.rstrip("/") + "/oauth/token"

    @property
    def base_url(self) -> str:
        """Service base URL (alias for service_url, used by XsuaaAuthProvider)."""
        return self.service_url

    @property
    def identityzone(self) -> None:
        """No identity zone — auditlog does not support tenant substitution."""
        return None


@dataclass
class BindingData:
    """Internal class for parsing SAP service binding data.

    Service bindings contain a JSON string with OAuth2 credentials
    embedded in the 'uaa' field. This class extracts those credentials
    and returns a flat AuditLogConfig.
    """

    url: str = ""
    uaa: str = ""

    def validate(self) -> None:
        """Validate that all required fields are set."""
        if not self.url:
            raise ValueError("url is required")
        if not self.uaa:
            raise ValueError("uaa field is required")

    def extract_config(self) -> AuditLogConfig:
        """Parse the UAA JSON string and return a flat AuditLogConfig.

        The UAA field contains a JSON string with OAuth2 credentials:
        {"clientid": "...", "clientsecret": "...", "url": "..."}

        Returns:
            AuditLogConfig: Flat configuration with all credentials

        Raises:
            ClientCreationError: If JSON parsing fails
        """
        if not self.uaa:
            raise ClientCreationError("UAA field is empty")

        try:
            uaa_data = json.loads(self.uaa, strict=False)
        except json.JSONDecodeError as e:
            raise ClientCreationError(f"Failed to parse UAA JSON: {e}")

        # Flatten configuration so it looks the same as customer-provided
        try:
            return AuditLogConfig(
                client_id=uaa_data["clientid"],
                client_secret=uaa_data["clientsecret"],
                oauth_url=uaa_data["url"],
                service_url=self.url,
            )
        except KeyError as e:
            raise ClientCreationError(f"Missing required field in UAA JSON: {e}")


def _load_config_from_env() -> AuditLogConfig:
    """Load audit log configuration from environment/mounts.

    Uses the secret resolver to load configuration from:
    1. Mount path: /etc/secrets/appfnd
    2. Environment variable: CLOUD_SDK_CFG
    3. Service name: auditlog
    4. Instance: default

    Returns:
        AuditLogConfig: Flat configuration with all credentials

    Raises:
        ClientCreationError: If loading or parsing fails
    """
    from sap_cloud_sdk.core.secret_resolver import (
        read_from_mount_and_fallback_to_env_var,
    )

    try:
        # Load raw config data using secret resolver
        binding_data: BindingData = BindingData("", "")

        read_from_mount_and_fallback_to_env_var(
            base_volume_mount="/etc/secrets/appfnd",
            base_var_name="CLOUD_SDK_CFG",
            module="auditlog",
            instance="default",
            target=binding_data,
        )

        binding_data.validate()
        return binding_data.extract_config()

    except Exception as e:
        raise ClientCreationError(f"Failed to load configuration: {e}")


def _make_config_factory() -> "ConfigFactory[AuditLogConfig]":
    """Return a :class:`~sap_cloud_sdk.core.secret_resolver.ConfigFactory` for auditlog.

    The factory re-reads the binding on every call and tracks the secret
    directory mtime for proactive rotation detection.

    Returns:
        A callable that produces a fresh :class:`AuditLogConfig`.
    """
    from sap_cloud_sdk.core.secret_resolver import ConfigFactory

    def _extract(binding: BindingData) -> AuditLogConfig:
        try:
            return binding.extract_config()
        except ClientCreationError:
            raise
        except Exception as exc:
            raise ClientCreationError(
                f"Failed to load auditlog configuration: {exc}"
            ) from exc

    return ConfigFactory(
        module="auditlog",
        instance="default",
        binding_cls=BindingData,
        extract=_extract,
    )
