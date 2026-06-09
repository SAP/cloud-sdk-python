"""Configuration for SAP Data Anonymization Service.

Authentication uses a Key Store (client certificate) only — no OAuth2 credentials
are required. The certificate/key can be supplied in two ways:

1. **Inline Key Store** – set ``cert`` and ``key`` to base64-encoded PEM values.

2. **BTP Destination Key Store** – set ``destination_name`` to a BTP Destination
    that carries the client certificate; the transport fetches the certificate from
    the Destination service at runtime.

Environment variables / mount keys (loaded by secret_resolver from
``/etc/secrets/appfnd`` or ``CLOUD_SDK_CFG``):

    service_url          – base URL of the anonymization REST API
    cert                 – base64-encoded PEM client certificate value
    key                  – base64-encoded PEM private key value
    destination_name     – (alternative) BTP Destination name carrying the client cert
"""

from dataclasses import dataclass
from typing import Optional

from sap_cloud_sdk.core.data_anonymization.exceptions import ClientCreationError


@dataclass
class DataAnonymizationConfig:
    """Configuration for the Data Anonymization Service client.

    Required fields:
        service_url: Base URL of the anonymization REST API.

    Key Store fields (provide exactly one of the two options):
        cert + key:            Base64-encoded PEM certificate and private key.
        destination_name:      BTP Destination name that carries the client
                               certificate; the transport resolves the cert at
                               runtime via ``sap_cloud_sdk.destination``.
    """

    service_url: str

    # Key Store – inline base64 values
    cert: Optional[str] = None
    key: Optional[str] = None

    # Legacy file-based Key Store
    cert_path: Optional[str] = None
    key_path: Optional[str] = None

    # Key Store – BTP Destination
    destination_name: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.service_url:
            raise ValueError("service_url is required")

        has_inline_keystore = bool(self.cert) or bool(self.key)
        has_file_keystore = bool(self.cert_path) or bool(self.key_path)

        if (
            not has_inline_keystore
            and not has_file_keystore
            and not self.destination_name
        ):
            raise ValueError(
                "A Key Store is required: provide cert + key, "
                "cert_path + key_path, or destination_name"
            )
        if bool(self.cert) != bool(self.key):
            raise ValueError("cert and key must both be set together")
        if bool(self.cert_path) != bool(self.key_path):
            raise ValueError("cert_path and key_path must both be set together")


@dataclass
class _BindingData:
    """Internal: parses a SAP service-binding JSON for the anonymization service."""

    url: str
    cert: Optional[str] = None
    key: Optional[str] = None
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    destination_name: Optional[str] = None

    def validate(self) -> None:
        if not self.url:
            raise ValueError("url is required")

        has_inline_keystore = bool(self.cert) or bool(self.key)
        has_file_keystore = bool(self.cert_path) or bool(self.key_path)

        if (
            not has_inline_keystore
            and not has_file_keystore
            and not self.destination_name
        ):
            raise ValueError(
                "Binding must contain cert + key, cert_path + key_path, or destination_name"
            )

    def extract_config(self) -> DataAnonymizationConfig:
        return DataAnonymizationConfig(
            service_url=self.url,
            cert=self.cert,
            key=self.key,
            cert_path=self.cert_path,
            key_path=self.key_path,
            destination_name=self.destination_name,
        )


def _load_config_from_env(instance: str = "default") -> DataAnonymizationConfig:
    """Load anonymization config from environment / mount path.

    Uses the secret resolver to read from:
      - Mount: /etc/secrets/appfnd
      - Env var: CLOUD_SDK_CFG
      - Service: data-anonymization
      - Instance: *instance* (default "default")

    Returns:
        DataAnonymizationConfig

    Raises:
        ClientCreationError: If loading or parsing fails.
    """
    from sap_cloud_sdk.core.secret_resolver import (
        read_from_mount_and_fallback_to_env_var,
    )

    try:
        binding = _BindingData("")
        read_from_mount_and_fallback_to_env_var(
            "/etc/secrets/appfnd",
            "CLOUD_SDK_CFG",
            "data-anonymization",
            instance,
            binding,
        )
        binding.validate()
        return binding.extract_config()
    except Exception as e:
        raise ClientCreationError(f"Failed to load configuration: {e}")
