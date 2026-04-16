"""Configuration parsing for SAP Audit Log Service.

This module handles parsing of audit log configuration from SAP Cloud Platform
service bindings where OAuth2 credentials are embedded as JSON strings.
"""

import json
from dataclasses import dataclass

from sap_cloud_sdk.auditlog.exceptions import ClientCreationError


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


@dataclass
class BindingData:
    """Internal class for parsing SAP service binding data.

    Service bindings contain a JSON string with OAuth2 credentials
    embedded in the 'uaa' field. This class extracts those credentials
    and returns a flat AuditLogConfig.
    """

    url: str
    uaa: str

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
    from sap_cloud_sdk.secret_resolver import (
        read_from_mount_and_fallback_to_env_var,
    )

    try:
        # Load raw config data using secret resolver
        binding_data: BindingData = BindingData("", "")

        read_from_mount_and_fallback_to_env_var(
            "/etc/secrets/appfnd", "CLOUD_SDK_CFG", "auditlog", "default", binding_data
        )

        binding_data.validate()
        return binding_data.extract_config()

    except Exception as e:
        raise ClientCreationError(f"Failed to load configuration: {e}")
