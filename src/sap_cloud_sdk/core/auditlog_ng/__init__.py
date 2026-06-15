"""SAP Cloud SDK for Python - Audit Log NG (OTLP/gRPC) module

Sends audit log events as OpenTelemetry LogRecords over gRPC.
Supports mTLS (client certificates) and insecure (no-auth) modes.

The create_client() function accepts an AuditLogNGConfig and returns a
ready-to-use AuditClient.

Usage — explicit config::

    from sap_cloud_sdk.core.auditlog_ng import create_client, AuditLogNGConfig

    config = AuditLogNGConfig(
        endpoint="audit.example.com:443",
        deployment_id="my-deployment",
        namespace="namespace-123",
        cert_file="client.pem",
        key_file="client.key",
    )
    client = create_client(config=config)

Usage — resolve from a Destination::

    from sap_cloud_sdk.core.auditlog_ng import create_client

    client = create_client(
        destination_name="my-audit-destination",
        destination_instance="default",   # optional, defaults to "default"
        fragment_name="prod-fragment",    # optional
    )

    # Send an audit event (protobuf message)
    event_id = client.send(event, "DataAccess")
    client.close()
"""

from typing import Optional

from sap_cloud_sdk.core.auditlog_ng.client import AuditClient
from sap_cloud_sdk.core.auditlog_ng.config import (
    AuditLogNGConfig,
    SCHEMA_URL,
)
from sap_cloud_sdk.core.auditlog_ng.exceptions import (
    AuditLogNGError,
    ClientCreationError,
    ValidationError,
)

from sap_cloud_sdk.core.telemetry import (
    Module,
    Operation,
    record_error_metric as _record_error_metric,
)

_DESTINATION_PROP_DEPLOYMENT_ID = "deploymentId"
_DESTINATION_PROP_DEPLOYMENT_REGION = "deploymentRegion"
_DESTINATION_PROP_NAMESPACE = "namespace"


def _get_config_from_destination(
    destination_name: str,
    destination_instance: str,
    fragment_name: str,
) -> dict:
    """Resolve endpoint, deployment_id and namespace from a named Destination.

    The destination must expose these custom properties:

    - ``deploymentId`` (or ``deploymentRegion`` as fallback when absent/empty)
    - ``namespace``

    The destination ``url`` is used as the OTLP gRPC endpoint.

    Args:
        destination_name: Name of the destination to resolve.
        destination_instance: Destination service binding instance name.
            Passed to ``create_client(instance=...)``; ``None`` uses the default.
        fragment_name: Optional fragment merged before resolution.

    Returns:
        dict with keys ``endpoint``, ``deployment_id``, ``namespace``.

    Raises:
        ValueError: If the destination is not found or required properties
            are missing.
    """
    # Lazy import — keeps destination an optional dependency; importing auditlog_ng
    # in environments without the destination package continues to work.
    from sap_cloud_sdk.destination import (
        ConsumptionOptions,
        create_client as _dest_create_client,
    )

    dest_client = _dest_create_client()
    options = ConsumptionOptions(fragment_name=fragment_name)
    destination = dest_client.get_destination(
        name=destination_name, instance=destination_instance, options=options
    )

    if destination is None:
        raise ValueError(f"Destination '{destination_name}' was not found")

    endpoint = destination.url

    props = destination.properties

    deployment_id = props.get(_DESTINATION_PROP_DEPLOYMENT_ID) or ""
    if not deployment_id:
        deployment_id = props.get(_DESTINATION_PROP_DEPLOYMENT_REGION) or ""
    if not deployment_id:
        raise ValueError(
            f"Destination '{destination_name}' must provide either the "
            f"'{_DESTINATION_PROP_DEPLOYMENT_ID}' or "
            f"'{_DESTINATION_PROP_DEPLOYMENT_REGION}' property"
        )

    namespace = props.get(_DESTINATION_PROP_NAMESPACE) or ""
    if not namespace:
        raise ValueError(
            f"Destination '{destination_name}' must provide the "
            f"'{_DESTINATION_PROP_NAMESPACE}' property"
        )

    return {
        "endpoint": endpoint,
        "deployment_id": deployment_id,
        "namespace": namespace,
    }


def create_client(
    *,
    config: Optional[AuditLogNGConfig] = None,
    # Destination-based resolution
    destination_name: Optional[str] = None,
    destination_instance: Optional[str] = None,
    fragment_name: Optional[str] = None,
    # Explicit connection parameters
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

    Three mutually exclusive ways to provide configuration (evaluated in order):

    1. **Explicit config object** — pass a pre-built :class:`AuditLogNGConfig`
       via ``config``; all other keyword arguments are ignored.

    2. **Destination-based resolution** — pass ``destination_name``,
    ``destination_instance`` and ``fragment_name``).  The Destination
       module is used to fetch the named destination and extract ``endpoint``,
       ``deployment_id`` (with fallback to ``deploymentRegion``), and

        ``namespace`` from its properties.  The remaining keyword arguments
       (``cert_file``, ``key_file``, ``ca_file``, ``insecure``, ``service_name``,
       ``batch``, ``compression``, ``schema_url``) are still forwarded to the
       resulting :class:`AuditLogNGConfig`.

    3. **Explicit keyword arguments** — pass ``endpoint``, ``deployment_id``,
       and ``namespace`` directly.

    Args:
        _telemetry_source: Internal parameter for telemetry. Not for external use.
        config: Optional explicit configuration. If provided, all other
                keyword arguments are ignored.
        destination_name: Name of the SAP Destination to resolve.
        destination_instance: Destination service binding instance name used
        fragment_name: destination fragment
        When set, ``destination_name``, ``destination_instance`` and ``fragment_name``
        are used to resolve ``endpoint`` / ``deployment_id`` / ``namespace`` arguments.
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
        ValueError: If required parameters are missing or destination
                resolution fails.
    """
    try:
        if config is None:
            try:
                if destination_name and destination_instance and fragment_name:
                    resolved = _get_config_from_destination(
                        destination_name=destination_name,
                        destination_instance=destination_instance,
                        fragment_name=fragment_name,
                    )
                    endpoint = resolved["endpoint"]
                    deployment_id = resolved["deployment_id"]
                    namespace = resolved["namespace"]
                else:
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
            except Exception:
                _record_error_metric(
                    Module.AUDITLOG_NG,
                    _telemetry_source,
                    Operation.AUDITLOG_CREATE_CLIENT,
                )
                raise

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
