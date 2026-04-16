"""SAP Cloud SDK for Python - Audit Log NG (OTLP/gRPC) module

Sends audit log events as OpenTelemetry LogRecords over gRPC.
Supports mTLS (client certificates) and insecure (no-auth) modes.

The create_client() function accepts an AuditLogNGConfig and returns a
ready-to-use AuditClient.

Usage:
    from sap_cloud_sdk.auditlog_ng import create_client, AuditLogNGConfig

    config = AuditLogNGConfig(
        endpoint="audit.example.com:443",
        deployment_id="my-deployment",
        namespace="namespace-123",
        cert_file="client.pem",
        key_file="client.key",
    )
    client = create_client(config=config)

    # Send an audit event (protobuf message)
    event_id = client.send(event, "DataAccess")
    client.close()
"""

from typing import Optional

from sap_cloud_sdk.auditlog_ng.client import AuditClient
from sap_cloud_sdk.auditlog_ng.config import (
    AuditLogNGConfig,
    SCHEMA_URL,
)
from sap_cloud_sdk.auditlog_ng.exceptions import (
    AuditLogNGError,
    ClientCreationError,
    ValidationError,
)

from sap_cloud_sdk.telemetry import Module, Operation, record_metrics


@record_metrics(Module.AUDITLOG_NG, Operation.AUDITLOG_CREATE_CLIENT)
def create_client(
    *,
    config: Optional[AuditLogNGConfig] = None,
    endpoint: Optional[str] = None,
    deployment_id: Optional[str] = None,
    namespace: Optional[str] = None,
    cert_file: Optional[str] = None,
    key_file: Optional[str] = None,
    ca_file: Optional[str] = None,
    insecure: bool = False,
    service_name: str = "audit-client",
    batch: bool = False,
    compression: bool = True,
    schema_url: str = SCHEMA_URL,
    _telemetry_source: Optional[Module] = None,
) -> AuditClient:
    """Create an AuditClient for sending audit events over OTLP/gRPC.

    Either pass a pre-built ``config`` **or** the individual keyword arguments.
    When ``config`` is provided the remaining keyword arguments are ignored.

    Args:
        _telemetry_source: Internal parameter for telemetry. Not for external use.
        config: Optional explicit configuration. If provided, all other
                keyword arguments are ignored.
        endpoint: OTLP gRPC endpoint (``host:port``).
        deployment_id: Deployment identifier.
        namespace: Namespace identifier.
        cert_file: Path to client certificate (PEM) for mTLS.
        key_file: Path to client private key (PEM) for mTLS.
        ca_file: Path to CA certificate (PEM) for server verification.
        insecure: Use insecure connection (no TLS).
        service_name: OpenTelemetry ``service.name`` resource attribute.
        batch: Use batch processing (better throughput, slight delay).
        compression: Enable gzip compression.
        schema_url: OpenTelemetry schema URL for the logger.

    Returns:
        AuditClient: Configured client ready for audit operations.

    Raises:
        ClientCreationError: If client creation fails.
        ValueError: If required parameters are missing.
    """
    try:
        if config is None:
            if not endpoint or not deployment_id or not namespace:
                raise ValueError(
                    "endpoint, deployment_id, and namespace are required "
                    "when config is not provided"
                )
            config = AuditLogNGConfig(
                endpoint=endpoint,
                deployment_id=deployment_id,
                namespace=namespace,
                cert_file=cert_file,
                key_file=key_file,
                ca_file=ca_file,
                insecure=insecure,
                service_name=service_name,
                batch=batch,
                compression=compression,
                schema_url=schema_url,
            )

        return AuditClient(config, _telemetry_source=_telemetry_source)

    except (ValueError, ValidationError) as e:
        raise e
    except Exception as e:
        raise ClientCreationError(f"Failed to create audit log NG client: {e}") from e


__all__ = [
    # Factory function
    "create_client",
    # Client
    "AuditClient",
    # Configuration
    "AuditLogNGConfig",
    # Exceptions
    "AuditLogNGError",
    "ClientCreationError",
    "ValidationError",
]
