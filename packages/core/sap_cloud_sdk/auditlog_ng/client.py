"""Audit Log OTLP Client.

Sends audit log events as OpenTelemetry LogRecords over gRPC.
Supports mTLS (client certificates) and insecure (no-auth) modes.
"""

import json
import uuid
from typing import Optional

import protovalidate
from protovalidate import ValidationError as ProtoValidationError

import grpc
from google.protobuf.message import Message
from google.protobuf.json_format import MessageToDict
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    SimpleLogRecordProcessor,
    BatchLogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry._logs.severity import SeverityNumber

from sap_cloud_sdk.auditlog_ng.config import (
    AuditLogNGConfig,
    _validate_source_arg,
)
from sap_cloud_sdk.auditlog_ng.exceptions import ValidationError
from sap_cloud_sdk.telemetry import Module


class AuditClient:
    """OTLP-based audit log client.

    Wraps protobuf audit events in OpenTelemetry LogRecords and sends
    them over gRPC to an OTLP-compatible endpoint.

    Note:
        Do not instantiate this class directly. Use the
        :func:`~sap_cloud_sdk.auditlog_ng.create_client` factory function
        instead, which handles proper configuration.

    Example::

        from sap_cloud_sdk.auditlog_ng import create_client

        client = create_client(config=AuditLogNGConfig(
            endpoint="audit.example.com:443",
            deployment_id="my-deployment",
            namespace="namespace-123",
            cert_file="client.pem",
            key_file="client.key",
        ))

        event_id = client.send(event, "DataAccess")
        client.close()
    """

    def __init__(
        self, config: AuditLogNGConfig, _telemetry_source: Optional[Module] = None
    ) -> None:
        """Initialize the audit client from a config object.

        Args:
            config: Fully-validated :class:`AuditLogNGConfig`.
        """
        self._config = config
        self._telemetry_source = _telemetry_source
        self._closed = False

        # Build gRPC credentials
        credentials = self._build_credentials(config)

        # Create OTLP exporter
        self._exporter = OTLPLogExporter(
            endpoint=config.endpoint,
            insecure=config.insecure,
            credentials=credentials,
            compression=(
                grpc.Compression.Gzip
                if config.compression
                else grpc.Compression.NoCompression
            ),
        )

        # Create logger provider
        self._provider = LoggerProvider(
            resource=Resource.create(
                {
                    "service.name": config.service_name,
                    "sap.ucl.deployment_id": config.deployment_id,
                    "sap.ucl.system_namespace": config.namespace,
                }
            )
        )

        # Add processor
        processor = (
            BatchLogRecordProcessor(self._exporter)
            if config.batch
            else SimpleLogRecordProcessor(self._exporter)
        )
        self._provider.add_log_record_processor(processor)

        self._logger = self._provider.get_logger(
            "auditlog",
            schema_url=config.schema_url,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send(
        self,
        event: Message,
        event_type: Optional[str] = None,
        format: str = "protobuf-binary",
    ) -> str:
        """Send an audit log event.

        Args:
            event: Protobuf message (audit event).
            event_type: Event type name (defaults to message type name).
            format: Serialization format (``"protobuf-binary"`` or ``"json"``).

        Returns:
            Generated event ID (UUID).

        Raises:
            RuntimeError: If the client has already been closed.
            ValueError: If *format* is not a supported value.
            ValidationError: If the protobuf event fails validation.

        Note:
            A successful return does not guarantee delivery.
            The OTLP exporter operates asynchronously. Always use flush() before shutdown to maximize delivery probability.
        """
        if self._closed:
            raise RuntimeError("Client is closed")

        if format not in {"protobuf-binary", "json"}:
            raise ValueError("format must be 'protobuf-binary' or 'json'")

        try:
            protovalidate.validate(event)
        except ProtoValidationError as e:
            raise ValidationError(f"Audit event validation failed: {e}") from e

        common = getattr(event, "common", None)
        tenant_id = getattr(common, "tenant_id", None)
        if not isinstance(tenant_id, str):
            raise ValueError("Event must contain common.tenant_id as a string")
        _validate_source_arg(tenant_id, "tenant_id")

        event_id = str(uuid.uuid4())

        if event_type is None:
            descriptor = getattr(event, "DESCRIPTOR", None)
            descriptor_name = getattr(descriptor, "name", None)
            if not isinstance(descriptor_name, str) or not descriptor_name:
                raise ValueError(
                    "Could not determine event type from message descriptor"
                )
            event_type = descriptor_name

        event_type = f"sap.als.AuditEvent.{event_type}.v2"

        if format == "json":
            mime_type = "application/json"
            event_dict = MessageToDict(event, preserving_proto_field_name=False)
            body = json.dumps(event_dict)
        else:
            mime_type = "application/protobuf"
            body = event.SerializeToString()

        # Emit log record
        self._logger.emit(
            severity_number=SeverityNumber.INFO,
            event_name=event_type,
            body=body,
            attributes={
                "cloudevents.event_id": event_id,
                "sap.tenancy.tenant_id": tenant_id,
                "sap.auditlogging.mime_type": mime_type,
            },
        )

        return event_id

    def send_json(self, event: Message, event_type: Optional[str] = None) -> str:
        """Send event in JSON format."""
        return self.send(event, event_type, format="json")

    def flush(self) -> None:
        """Flush pending events (for batch mode)."""
        if not self._closed:
            self._provider.force_flush()

    def close(self) -> None:
        """Shutdown the client and flush pending events."""
        if not self._closed:
            self._provider.shutdown()
            self._closed = True

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "AuditClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_credentials(
        config: AuditLogNGConfig,
    ) -> Optional[grpc.ChannelCredentials]:
        """Build gRPC channel credentials from config."""
        if config.insecure:
            return None

        root_certs = None
        private_key = None
        cert_chain = None

        if config.ca_file:
            with open(config.ca_file, "rb") as f:
                root_certs = f.read()

        if config.cert_file and config.key_file:
            with open(config.key_file, "rb") as f:
                private_key = f.read()
            with open(config.cert_file, "rb") as f:
                cert_chain = f.read()

        return grpc.ssl_channel_credentials(
            root_certificates=root_certs,
            private_key=private_key,
            certificate_chain=cert_chain,
        )
