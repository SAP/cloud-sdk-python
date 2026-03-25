import logging
import os

from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from traceloop.sdk import Traceloop

from sap_cloud_sdk.core.telemetry import Module, Operation
from sap_cloud_sdk.core.telemetry.config import (
    create_resource_attributes_from_env,
    _get_app_name,
)
from sap_cloud_sdk.core.telemetry.genai_attribute_transformer import (
    GenAIAttributeTransformer,
)
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics

logger = logging.getLogger(__name__)


@record_metrics(Module.AICORE, Operation.AICORE_AUTO_INSTRUMENT)
def auto_instrument():
    """
    Initialize meta-instrumentation for GenAI tracing. Should be initialized before any AI frameworks.

    Traces are exported to the OTEL collector endpoint configured in environment with
    OTEL_EXPORTER_OTLP_ENDPOINT, or printed to console when OTEL_TRACES_EXPORTER=console.
    """
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    console_traces = os.getenv("OTEL_TRACES_EXPORTER", "").lower() == "console"

    if not otel_endpoint and not console_traces:
        logger.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT not set. Instrumentation will be disabled."
        )
        return

    if console_traces:
        logger.info("Initializing auto instrumentation with console exporter")
        base_exporter = ConsoleSpanExporter()
    else:
        if "v1/traces" not in otel_endpoint:
            otel_endpoint = otel_endpoint.rstrip("/") + "/v1/traces"
        protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc").lower()
        if protocol == "grpc":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
        elif protocol == "http/protobuf":
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
        else:
            raise ValueError(
                f"Unsupported OTEL_EXPORTER_OTLP_PROTOCOL: '{protocol}'. "
                "Supported values are 'grpc' and 'http/protobuf'."
            )

        logger.info(
            f"Initializing auto instrumentation with endpoint: {otel_endpoint} "
            f"(protocol: {protocol})"
        )
        base_exporter = OTLPSpanExporter(endpoint=otel_endpoint)

    exporter = GenAIAttributeTransformer(base_exporter)

    resource = create_resource_attributes_from_env()
    Traceloop.init(
        app_name=_get_app_name(),
        exporter=exporter,
        resource_attributes=resource,
        should_enrich_metrics=True,
        disable_batch=True,
    )

    logger.info("Cloud auto instrumentation initialized successfully")
