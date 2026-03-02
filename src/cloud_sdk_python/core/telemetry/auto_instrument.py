import logging
import os
from typing import Optional

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from traceloop.sdk import Traceloop

from cloud_sdk_python.core.telemetry import Module, Operation
from cloud_sdk_python.core.telemetry.config import create_resource_attributes_from_env, _get_conhos_app_name
from cloud_sdk_python.core.telemetry.genai_attribute_transformer import (
    GenAIAttributeTransformer,
)
from cloud_sdk_python.core.telemetry.metrics_decorator import record_metrics

logger = logging.getLogger(__name__)


@record_metrics(Module.AICORE, Operation.AICORE_AUTO_INSTRUMENT)
def auto_instrument():
    """
    Initialize meta-instrumentation for GenAI tracing. Should be initialized before any AI frameworks.

    Traces are exported to the OTEL collector endpoint configured in environment with OTEL_EXPORTER_OTLP_ENDPOINT.

    Args:
    """
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if not otel_endpoint:
        logger.warning("OTEL_EXPORTER_OTLP_ENDPOINT not set. Instrumentation will be disabled.")
        return

    if "v1/traces" not in otel_endpoint:
        otel_endpoint = otel_endpoint.rstrip("/") + "/v1/traces"

    logger.info(f"Initializing auto instrumentation with endpoint: {otel_endpoint}")

    base_exporter = OTLPSpanExporter(endpoint=otel_endpoint)
    exporter = GenAIAttributeTransformer(base_exporter)

    resource = create_resource_attributes_from_env()
    Traceloop.init(app_name=_get_conhos_app_name(),
                   exporter=exporter,
                   resource_attributes=resource,
                   should_enrich_metrics=True,
                   disable_batch=True)

    logger.info("Cloud auto instrumentation initialized successfully")
