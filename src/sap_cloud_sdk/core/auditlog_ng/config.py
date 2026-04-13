"""Configuration and validation for SAP Audit Log NG (OTLP/gRPC) Service.

This module handles configuration dataclasses and input validation
for the OTLP-based audit log client.
"""

import re
from dataclasses import dataclass
from typing import Optional

SCHEMA_URL = "https://github.tools.sap/wg-observability/telemetry-semantic-conventions/blob/audit_event_catalog_v2.1.2/payload-specifications/audit-logging/sap/auditlog/auditevent/v2/auditevent.proto"

_SOURCE_ARG_PATTERN = re.compile(r"[a-zA-Z0-9._/~-]+")


def _validate_source_arg(value: str, name: str) -> None:
    """Validate that *value* only contains characters in ``[a-zA-Z0-9._-/~]``.

    Args:
        value: The string to validate.
        name: Human-readable parameter name (used in the error message).

    Raises:
        ValueError: If the value contains invalid characters.
    """
    if not _SOURCE_ARG_PATTERN.fullmatch(value):
        raise ValueError(
            f"{name} must only contain characters from [a-zA-Z0-9._-/~]. "
            f"Invalid value: {value}"
        )


@dataclass
class AuditLogNGConfig:
    """Audit Log NG client configuration.

    Groups every knob accepted by :class:`AuditClient` so that callers can
    build a configuration object independently of the client instantiation.

    Args:
        endpoint: OTLP gRPC endpoint (``host:port``).
        deployment_id: Deployment identifier (validated against allowed character set).
        namespace: Namespace identifier (validated against allowed character set).
        cert_file: Path to client certificate (PEM) for mTLS.
        key_file: Path to client private key (PEM) for mTLS.
        ca_file: Path to CA certificate (PEM) for server verification.
        insecure: Use insecure connection (no TLS) — for local testing.
        service_name: OpenTelemetry ``service.name`` resource attribute.
        batch: Use batch processing (better throughput, slight delay).
        compression: Enable gzip compression.
        schema_url: OpenTelemetry schema URL for the logger.
    """

    endpoint: str
    deployment_id: str
    namespace: str
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    ca_file: Optional[str] = None
    insecure: bool = False
    service_name: str = "audit-client"
    batch: bool = False
    compression: bool = True
    schema_url: str = SCHEMA_URL

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.endpoint:
            raise ValueError("endpoint is required")
        _validate_source_arg(self.deployment_id, "deployment_id")
        _validate_source_arg(self.namespace, "namespace")
