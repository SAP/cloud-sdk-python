"""Configuration for OpenTelemetry telemetry."""

import os
from dataclasses import dataclass
from typing import Optional
from opentelemetry.sdk.resources import SERVICE_NAME
from sap_cloud_sdk._version import get_version
from sap_cloud_sdk.telemetry.constants import (
    ATTR_SERVICE_INSTANCE_ID,
    ATTR_SERVICE_NAME,
    ATTR_DEPLOYMENT_ENVIRONMENT,
    ATTR_CLOUD_REGION,
    ATTR_SAP_SUBACCOUNT_ID,
    ATTR_SAP_SYSTEM_ROLE,
    ATTR_SAP_SDK_NAME,
    ATTR_SAP_SDK_LANGUAGE,
    ATTR_SAP_SDK_VERSION,
    SDK_NAME,
)

# Default attribute values
DEFAULT_UNKNOWN = "unknown"

# Environment variable keys
ENV_REGION = "APPFND_CONHOS_REGION"
ENV_ENVIRONMENT = "APPFND_CONHOS_ENVIRONMENT"
ENV_SUBACCOUNT_ID = "APPFND_CONHOS_SUBACCOUNTID"
ENV_APP_NAME = "APPFND_CONHOS_APP_NAME"
ENV_HOSTNAME = "HOSTNAME"
ENV_SYSTEM_ROLE = "APPFND_CONHOS_SYSTEM_ROLE"

# OTEL environment variable keys
ENV_OTLP_ENDPOINT = "OTEL_EXPORTER_OTLP_ENDPOINT"
ENV_TRACES_EXPORTER = "OTEL_TRACES_EXPORTER"
ENV_OTLP_PROTOCOL = "OTEL_EXPORTER_OTLP_PROTOCOL"
ENV_OTEL_DISABLED = "CLOUD_SDK_OTEL_DISABLED"


def _get_region() -> str:
    """Get region from environment or return default."""
    return os.getenv(ENV_REGION, DEFAULT_UNKNOWN)


def _get_environment() -> str:
    """Get environment from environment or return default."""
    return os.getenv(ENV_ENVIRONMENT, DEFAULT_UNKNOWN)


def _get_subaccount_id() -> str:
    """Get subaccount ID from environment or return default."""
    return os.getenv(ENV_SUBACCOUNT_ID, DEFAULT_UNKNOWN)


def _get_app_name() -> str:
    """Get application name from environment or return default."""
    return os.getenv(ENV_APP_NAME, DEFAULT_UNKNOWN)


def _get_hostname() -> str:
    """Get hostname from environment or return default."""
    return os.getenv(ENV_HOSTNAME, DEFAULT_UNKNOWN)


def _get_system_role() -> str:
    """Get system role from environment or return default.

    Returns:
        System role from APPFND_CONHOS_SYSTEM_ROLE environment variable,
        or "ZAFT" if not set.
    """
    return os.getenv(ENV_SYSTEM_ROLE, DEFAULT_UNKNOWN)


def create_resource_attributes_from_env() -> dict:
    """Create OpenTelemetry Resource with SDK attributes.

    This function creates a Resource with all standard SDK resource attributes,
    ensuring consistency between metrics and traces. Resource attributes are
    static and set once at startup.

    Returns:
        Resource with SDK resource attributes including:
        - service.name (from APPFND_CONHOS_APP_NAME, defaults to "unknown")
        - service.instance.id (from HOSTNAME, defaults to "unknown")
        - deployment.environment.name (from APPFND_CONHOS_ENVIRONMENT, defaults to "unknown")
        - cloud.region (from APPFND_CONHOS_REGION, defaults to "unknown")
        - sap.cld.subaccount_id (from APPFND_CONHOS_SUBACCOUNTID, defaults to "unknown")
        - sap.cld.system_role (from APPFND_CONHOS_SYSTEM_ROLE, defaults to "ZAFT")
        - sap.cloud_sdk.name (constant: "SAP Cloud SDK for Python")
        - sap.cloud_sdk.language (constant: "python")
        - sap.cloud_sdk.version (from package version)
    """

    attributes = {
        SERVICE_NAME: _get_app_name(),
        ATTR_SERVICE_INSTANCE_ID: _get_hostname(),
        ATTR_SERVICE_NAME: _get_app_name(),
        ATTR_DEPLOYMENT_ENVIRONMENT: _get_environment(),
        ATTR_CLOUD_REGION: _get_region(),
        ATTR_SAP_SUBACCOUNT_ID: _get_subaccount_id(),
        ATTR_SAP_SYSTEM_ROLE: _get_system_role(),
        ATTR_SAP_SDK_NAME: SDK_NAME,
        ATTR_SAP_SDK_LANGUAGE: "python",
        ATTR_SAP_SDK_VERSION: get_version(),
    }

    return attributes


@dataclass
class InstrumentationConfig:
    """Configuration for OpenTelemetry telemetry.

    Telemetry is DISABLED by default to avoid connection overhead.
    Set OTEL_EXPORTER_OTLP_ENDPOINT to enable telemetry.

    Attributes:
        enabled: Whether telemetry is enabled. Defaults to False (disabled).
        service_name: Name of the service for telemetry. Fixed as 'application-foundation-sdk'.
        otlp_endpoint: OTLP endpoint URL for exporting metrics. Must be set to enable telemetry.
    """

    enabled: bool = False
    service_name: str = "application-foundation-sdk"
    otlp_endpoint: str = ""

    @classmethod
    def from_env(cls) -> "InstrumentationConfig":
        """Create configuration from environment variables.

        Telemetry is disabled by default. To enable:
        1. Set OTEL_EXPORTER_OTLP_ENDPOINT to your collector endpoint
        2. Can be explicitly disabled with CLOUD_SDK_OTEL_DISABLED=true

        Environment Variables:
            OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint URL (required to enable telemetry)
            CLOUD_SDK_OTEL_DISABLED: Set to 'true' to explicitly disable telemetry (optional)

        Returns:
            InstrumentationConfig instance with values from environment or defaults.
        """
        # Get OTLP endpoint - if not set, telemetry is disabled
        otlp_endpoint = os.getenv(ENV_OTLP_ENDPOINT, "")

        # Enable telemetry only if endpoint is configured
        # Can be explicitly disabled with CLOUD_SDK_OTEL_DISABLED=true
        enabled = (
            bool(otlp_endpoint)
            and os.getenv(ENV_OTEL_DISABLED, "false").lower() != "true"
        )

        return cls(
            enabled=enabled,
            service_name=_get_app_name(),
            otlp_endpoint=otlp_endpoint,
        )


# Global configuration instance
_config: Optional[InstrumentationConfig] = None


def get_config() -> InstrumentationConfig:
    """Get the global telemetry configuration.

    Returns:
        InstrumentationConfig instance.
    """
    global _config
    if _config is None:
        _config = InstrumentationConfig.from_env()
    return _config


def set_config(config: InstrumentationConfig) -> None:
    """Set the global telemetry configuration.

    Args:
        config: InstrumentationConfig instance to use.
    """
    global _config
    _config = config
