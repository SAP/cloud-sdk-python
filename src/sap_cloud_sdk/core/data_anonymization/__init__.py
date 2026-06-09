"""SAP Cloud SDK extension – Data Anonymization module.

Telemetry for this module is limited to operation-level metrics. Sensitive
payloads such as source text, pseudonymization metadata, file contents, or
certificate material are never emitted as telemetry attributes.

Usage::

    from sap_cloud_sdk.core.data_anonymization import (
        create_client,
        AnonymizeRequest,
        PseudonymizeRequest,
    )

    # Auto-detect config from environment / mount
    client = create_client()

    # Anonymize (irreversible)
    result = client.anonymize(AnonymizeRequest(text="John Doe, john@example.com"))
    assert result.result is not None

    # Pseudonymize (reversible)
    pseudo = client.pseudonymize(PseudonymizeRequest(text="John Doe"))
    assert pseudo.result is not None
    assert len(pseudo.metadata) >= 0

    # Explicit config with inline base64 Key Store
    from sap_cloud_sdk.core.data_anonymization import DataAnonymizationConfig
    cfg = DataAnonymizationConfig(
        service_url="https://anonymization.example.com",
        cert="<base64-encoded-client-certificate>",
        key="<base64-encoded-client-private-key>",
    )
    client = create_client(config=cfg)

    # BTP Destination Key Store (cloud)
    client = create_client(config=DataAnonymizationConfig(
        service_url="https://anonymization.example.com",
        destination_name="my-anonymization-dest",
    ))
"""

from typing import Optional

from sap_cloud_sdk.core.data_anonymization.client import DataAnonymizationClient
from sap_cloud_sdk.core.data_anonymization.config import (
    DataAnonymizationConfig,
    _load_config_from_env,
)
from sap_cloud_sdk.core.data_anonymization._http_transport import HttpTransport
from sap_cloud_sdk.core.data_anonymization.models import (
    AnonymizeTextRequest,
    AnonymizeFileRequest,
    AnonymizeRequest,
    AnonymizeFileResult,
    AnonymizeResult,
    FileOperationResult,
    PseudonymizeTextRequest,
    PseudonymizeFileRequest,
    PseudonymizeRequest,
    PseudonymizeFileResult,
    PseudonymizeResult,
    EntityMapping,
)
from sap_cloud_sdk.core.data_anonymization.exceptions import (
    DataAnonymizationError,
    ClientCreationError,
    TransportError,
    AuthenticationError,
)
from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics


@record_metrics(
    Module.DATA_ANONYMIZATION,
    Operation.DATA_ANONYMIZATION_CREATE_CLIENT,
)
def create_client(
    *,
    config: Optional[DataAnonymizationConfig] = None,
    instance: str = "default",
    _telemetry_source: Optional[Module] = None,
) -> DataAnonymizationClient:
    """Create a DataAnonymizationClient with automatic configuration detection.

    Args:
        config: Optional explicit DataAnonymizationConfig. When omitted the
                config is loaded from environment variables / secret mounts.
        instance: Service instance name used for secret resolution when
                  *config* is not provided. Defaults to ``"default"``.
        _telemetry_source: Internal parameter; not for end-user use.

    Returns:
        DataAnonymizationClient ready for anonymize / pseudonymize calls.

    Raises:
        ClientCreationError: If client creation fails.

    Note:
        Telemetry for client creation records only module/operation metadata and
        never includes configuration values or processed user content.
    """
    try:
        resolved = config if config is not None else _load_config_from_env(instance)
        transport = HttpTransport(resolved)
        return DataAnonymizationClient(transport, _telemetry_source=_telemetry_source)
    except Exception as e:
        raise ClientCreationError(
            f"Failed to create DataAnonymizationClient: {e}"
        ) from e


__all__ = [
    # Factory
    "create_client",
    # Client
    "DataAnonymizationClient",
    # Config
    "DataAnonymizationConfig",
    # Request / response models
    "AnonymizeTextRequest",
    "AnonymizeRequest",
    "AnonymizeFileRequest",
    "AnonymizeFileResult",
    "AnonymizeResult",
    "FileOperationResult",
    "PseudonymizeTextRequest",
    "PseudonymizeRequest",
    "PseudonymizeFileRequest",
    "PseudonymizeFileResult",
    "PseudonymizeResult",
    "EntityMapping",
    # Exceptions
    "DataAnonymizationError",
    "ClientCreationError",
    "TransportError",
    "AuthenticationError",
]
