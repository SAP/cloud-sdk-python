import logging
import os
from collections.abc import Mapping

from sap_cloud_sdk.core.telemetry.middleware.base import TelemetryMiddleware

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GRPCSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPSpanExporter,
)
from opentelemetry.processor.baggage import ALLOW_ALL_BAGGAGE_KEYS, BaggageSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SpanExporter
from traceloop.sdk import Traceloop

from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.operation import Operation
from sap_cloud_sdk.core.telemetry.config import (
    ENV_OTLP_ENDPOINT,
    ENV_OTLP_PROTOCOL,
    ENV_TRACES_EXPORTER,
    _get_app_name,
    create_resource_attributes_from_env,
)
from sap_cloud_sdk.core.telemetry.genai_attribute_transformer import (
    GenAIAttributeTransformer,
)
from sap_cloud_sdk.core.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.core.telemetry.propagated_attributes_processor import (
    PropagatedAttributesSpanProcessor,
)

logger = logging.getLogger(__name__)


@record_metrics(Module.AICORE, Operation.AICORE_AUTO_INSTRUMENT)
def auto_instrument(
    disable_batch: bool = False,
    middlewares: list[TelemetryMiddleware] | None = None,
):
    """
    Initialize meta-instrumentation for GenAI tracing. Should be initialized before any AI frameworks.

    Traces are exported to the OTEL collector endpoint configured in environment with
    OTEL_EXPORTER_OTLP_ENDPOINT, or printed to console when OTEL_TRACES_EXPORTER=console.

    Args:
        disable_batch: If True, uses SimpleSpanProcessor (synchronous, lower throughput).
                       Defaults to False, which uses BatchSpanProcessor (asynchronous,
                       recommended for production workloads).
        middlewares: Optional list of TelemetryMiddleware instances. When provided,
                     each middleware is registered with its application and a
                     MiddlewareSpanProcessor is added so that headers extracted by
                     the middlewares appear as attributes on every span.
                     Must be called before the ASGI application begins serving
                     requests so that register() runs before the first request.
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

    _merge_resource_attrs_into_active_provider_if_wrapper_installed(resource)

    _set_baggage_processor()

    if middlewares:
        _register_middleware_processors(middlewares)

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

    provider.add_span_processor(PropagatedAttributesSpanProcessor())
    logger.info("Registered PropagatedAttributesSpanProcessor for ContextVar attribute propagation")


def _register_middleware_processors(middlewares: list[TelemetryMiddleware]) -> None:
    from sap_cloud_sdk.core.telemetry.middleware.span_processor import (
        MiddlewareSpanProcessor,
    )

    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        logger.warning(
            "Unknown TracerProvider type. Skipping MiddlewareSpanProcessor registration"
        )
        return

    for middleware in middlewares:
        middleware.register()

    provider.add_span_processor(MiddlewareSpanProcessor(middlewares))
    logger.info(
        "Registered MiddlewareSpanProcessor for %d middleware(s)", len(middlewares)
    )


def _merge_resource_attrs_into_active_provider_if_wrapper_installed(
    sap_attrs: dict,
) -> None:
    """Merge sap-cloud-sdk resource attrs onto the active TracerProvider's
    Resource when an OTel auto-instrumentation wrapper has pre-installed it.

    Resource.merge direction puts ``sap_attrs`` on the right, so colliding
    keys (e.g. ``service.name``) are won by the sap-cloud-sdk side (e.g. the
    APPFND_CONHOS_APP_NAME-derived value beats the operator's
    k8s-deployment-derived default).

    Mutates ``provider._resource`` because OTel SDK exposes no public API
    to swap a TracerProvider's Resource post-construction.
    """
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        return
    existing_attrs = getattr(provider.resource, "attributes", None)
    if not isinstance(existing_attrs, Mapping):
        return
    if "telemetry.auto.version" not in existing_attrs:
        return

    provider._resource = provider.resource.merge(Resource.create(sap_attrs))
    logger.info(
        "Merged sap-cloud-sdk resource attrs onto wrapper-installed "
        "TracerProvider (marker: telemetry.auto.version)"
    )
