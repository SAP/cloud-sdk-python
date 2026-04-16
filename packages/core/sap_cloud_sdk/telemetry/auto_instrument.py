import logging
import os

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GRPCSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPSpanExporter,
)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.processor.baggage import ALLOW_ALL_BAGGAGE_KEYS, BaggageSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SpanExporter
from traceloop.sdk import Traceloop

from sap_cloud_sdk.telemetry import Module, Operation
from sap_cloud_sdk.telemetry.config import (
    create_resource_attributes_from_env,
    _get_app_name,
    ENV_OTLP_ENDPOINT,
    ENV_TRACES_EXPORTER,
    ENV_OTLP_PROTOCOL,
)
from sap_cloud_sdk.telemetry.genai_attribute_transformer import (
    GenAIAttributeTransformer,
)
from sap_cloud_sdk.telemetry.metrics_decorator import record_metrics

logger = logging.getLogger(__name__)


@record_metrics(Module.AICORE, Operation.AICORE_AUTO_INSTRUMENT)
def auto_instrument(disable_batch: bool = False):
    """
    Initialize meta-instrumentation for GenAI tracing. Should be initialized before any AI frameworks.

    Traces are exported to the OTEL collector endpoint configured in environment with
    OTEL_EXPORTER_OTLP_ENDPOINT, or printed to console when OTEL_TRACES_EXPORTER=console.

    Args:
        disable_batch: If True, uses SimpleSpanProcessor (synchronous, lower throughput).
                       Defaults to False, which uses BatchSpanProcessor (asynchronous,
                       recommended for production workloads).
    """
    otel_endpoint = os.getenv(ENV_OTLP_ENDPOINT, "")
    console_traces = os.getenv(ENV_TRACES_EXPORTER, "").lower() == "console"

    if not otel_endpoint and not console_traces:
        logger.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT not set. Instrumentation will be disabled."
        )
        return

    exporter = GenAIAttributeTransformer(_create_exporter())

    resource = create_resource_attributes_from_env()
    Traceloop.init(
        app_name=_get_app_name(),
        exporter=exporter,
        resource_attributes=resource,
        should_enrich_metrics=True,
        disable_batch=disable_batch,
    )

    _set_baggage_processor()

    logger.info("Cloud auto instrumentation initialized successfully")


def _create_exporter() -> SpanExporter:
    if os.getenv(ENV_TRACES_EXPORTER, "").lower() == "console":
        logger.info("Initializing auto instrumentation with console exporter")
        return ConsoleSpanExporter()

    endpoint = os.getenv(ENV_OTLP_ENDPOINT, "")
    protocol = os.getenv(ENV_OTLP_PROTOCOL, "grpc").lower()
    exporters = {"grpc": GRPCSpanExporter, "http/protobuf": HTTPSpanExporter}
    if protocol not in exporters:
        raise ValueError(
            f"Unsupported OTEL_EXPORTER_OTLP_PROTOCOL: '{protocol}'. "
            "Supported values are 'grpc' and 'http/protobuf'."
        )

    logger.info(
        f"Initializing auto instrumentation with endpoint: {endpoint} "
        f"(protocol: {protocol})"
    )
    return exporters[protocol]()


def _set_baggage_processor():
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        logger.warning("Unknown TracerProvider type. Skipping BaggageSpanProcessor")
        return

    provider.add_span_processor(BaggageSpanProcessor(ALLOW_ALL_BAGGAGE_KEYS))
    logger.info("Registered BaggageSpanProcessor for extension attribute propagation")
