"""SAP Cloud SDK for Python - Audit Log NG (OTLP/gRPC) module

Sends audit log events as OpenTelemetry LogRecords over gRPC.
Supports mTLS (client certificates) and insecure (no-auth) modes.

The create_client() function accepts an AuditLogNGConfig and returns a
ready-to-use AuditClient.

Usage:
    explicit config:

    from sap_cloud_sdk.core.auditlog_ng import create_client, AuditLogNGConfig

    config = AuditLogNGConfig(
        endpoint="audit.example.com:443",
        deployment_id="my-deployment",
        namespace="namespace-123",
        cert_file="client.pem",
        key_file="client.key",
    )
    client = create_client(config=config)

Usage:
    resolve from a Destination (requires tenant):

    from sap_cloud_sdk.core.auditlog_ng import create_client

    client = create_client(
        tenant="my-tenant-subdomain",
        destination_name="my-audit-destination",
        destination_instance="my-binding-instance",
        fragment_name="prod-fragment",    # optional
    )

Usage:
    explicit keyword arguments:

    from sap_cloud_sdk.core.auditlog_ng import create_client

    client = create_client(
        endpoint="audit.example.com:443",
        deployment_id="my-deployment",
        namespace="namespace-123",
    )

    # Send an audit event (protobuf message)
    event_id = client.send(event, "DataAccess")
    client.close()
"""

from typing import Optional
from enum import Enum

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


class _DestinationProperties(Enum):
    DEPLOYMENT_ID = "deploymentId"
    DEPLOYMENT_REGION = "deploymentRegion"
    NAMESPACE = "namespace"


def _get_config_from_destination(
    destination_name: Optional[str],
    destination_instance: Optional[str],
    fragment_name: Optional[str] = None,
    tenant: Optional[str] = None,
) -> dict[str, str]:
    """Resolve endpoint, deployment_id and namespace from a named Destination.

    The destination must expose these custom properties:

    - ``deploymentId`` (or ``deploymentRegion`` as fallback when absent/empty)
    - ``namespace``

    The destination ``url`` is used as the OTLP endpoint.
    The lookup is always performed at ``ConsumptionLevel.SUBACCOUNT``.

    Args:
        destination_name: Name of the destination to resolve.
        destination_instance: Destination service binding instance name,
            passed as ``instance=`` to ``destination.create_client()``.
        fragment_name: Optional fragment name merged into the destination
            before resolution. Wrapped in ``ConsumptionOptions`` when provided.
        tenant: Tenant subdomain forwarded as ``tenant=`` to
            ``get_destination()``.

    Returns:
        dict with keys ``endpoint``, ``deployment_id``, ``namespace``
        when destination is found, or an empty dict when not found.

    Raises:
        ValueError: If required properties (``deploymentId``/``deploymentRegion``
            or ``namespace``) are missing from the resolved destination.
    """
    # Lazy import — keeps destination an optional dependency; importing auditlog_ng
    # in environments without the destination package continues to work.
    from sap_cloud_sdk.destination import (
        ConsumptionOptions,
        ConsumptionLevel,
        create_client as _dest_create_client,
    )

    dest_client = _dest_create_client(instance=destination_instance)
    options = (
        ConsumptionOptions(
            fragment_name=fragment_name, fragment_level=ConsumptionLevel.SUBACCOUNT
        )
        if fragment_name
        else None
    )

    destination = dest_client.get_destination(
        name=destination_name,
        options=options,
        tenant=tenant,
        level=ConsumptionLevel.SUBACCOUNT,
    )

    if destination is None:
        return {}

    endpoint = destination.url
    props = destination.properties

    deployment_id = props.get(_DestinationProperties.DEPLOYMENT_ID.value) or ""
    if not deployment_id:
        deployment_id = props.get(_DestinationProperties.DEPLOYMENT_REGION.value) or ""
    if not deployment_id:
        raise ValueError(
            f"Destination '{destination_name}' must provide either the "
            f"'{_DestinationProperties.DEPLOYMENT_ID.value}' or "
            f"'{_DestinationProperties.DEPLOYMENT_REGION.value}' property"
        )

    namespace = props.get(_DestinationProperties.NAMESPACE.value) or ""
    if not namespace:
        raise ValueError(
            f"Destination '{destination_name}' must provide the "
            f"'{_DestinationProperties.NAMESPACE.value}' property"
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
    destination_name: Optional[str] = "AuditLogV3_Destination",
    destination_instance: Optional[str] = "default",
    fragment_name: Optional[str] = None,
    tenant: Optional[str] = None,
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

    2. **Destination-based resolution** — pass ``tenant`` (required to activate
       this path). ``destination_name`` and ``destination_instance`` identify
       the destination; ``fragment_name`` is optional. The Destination module
       resolves the named destination at subaccount level and extracts
       ``endpoint``, ``deployment_id`` (with fallback to ``deploymentRegion``),
       and ``namespace`` from its properties.

    3. **Explicit keyword arguments** — pass ``endpoint``, ``deployment_id``,
       and ``namespace`` directly (used when ``tenant`` is not provided).

    Args:
        _telemetry_source: Internal parameter for telemetry. Not for external use.
        config: Optional explicit configuration. If provided, all other
            keyword arguments are ignored.
        tenant: Tenant subdomain used for destination-based resolution.
            When provided, ``destination_name`` and ``destination_instance``
            are used to look up the destination.
        destination_name: Name of the SAP Destination to resolve. Only used
            when ``tenant`` is provided.
        destination_instance: Destination service binding instance name, passed
            as ``instance=`` to ``destination.create_client()``. Only used
            when ``tenant`` is provided.
        fragment_name: Optional destination fragment name merged before resolution.
        endpoint: OTLP endpoint (``host:port``). Required when ``tenant``
            is not provided and ``config`` is not given.
        deployment_id: Deployment identifier. Required when ``tenant`` is not
            provided and ``config`` is not given.
        namespace: Namespace identifier. Required when ``tenant`` is not
            provided and ``config`` is not given.
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
                if tenant:
                    resolved = _get_config_from_destination(
                        destination_name=destination_name,
                        destination_instance=destination_instance,
                        fragment_name=fragment_name,
                        tenant=tenant,
                    )
                    if resolved:
                        endpoint = resolved["endpoint"]
                        deployment_id = resolved["deployment_id"]
                        namespace = resolved["namespace"]
                else:
                    if not endpoint or not deployment_id or not namespace:
                        raise ValueError(
                            "endpoint, deployment_id, and namespace are required "
                            "when config or valid tenant subdomain is not provided"
                        )

                config = AuditLogNGConfig(
                    endpoint=endpoint or "",
                    deployment_id=deployment_id or "",
                    namespace=namespace or "",
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
