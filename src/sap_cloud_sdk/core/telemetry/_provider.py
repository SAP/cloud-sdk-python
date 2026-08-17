"""Internal module for setting up OpenTelemetry meter and logger providers."""

import logging
import os
from typing import Optional, cast

from opentelemetry import metrics
from opentelemetry._logs import get_logger_provider, set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter as GRPCLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as GRPCMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as HTTPLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as HTTPMetricExporter,
)
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import (
    MeterProvider,
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource

from sap_cloud_sdk.core.telemetry.config import (
    get_config,
    create_resource_attributes_from_env,
    ENV_OTLP_PROTOCOL,
)
from sap_cloud_sdk.core._version import get_version
from sap_cloud_sdk.core.telemetry.constants import SDK_PACKAGE_NAME

logger = logging.getLogger(__name__)


def _merge_sdk_resource_into_log_provider(
    provider: LoggerProvider, sdk_resource: Resource
) -> None:
    """OTel SDK has no public API to swap a LoggerProvider's Resource after construction."""
    provider._resource = provider.resource.merge(sdk_resource)
    with provider._active_loggers_lock:
        for logger_instance in provider._active_loggers:
            logger_instance._resource = provider._resource
    logger.info(
        "Merged sap-cloud-sdk resource attrs onto wrapper-installed LoggerProvider"
    )


def _root_logger_has_otel_handler() -> bool:
    # sitecustomize.py installs sdk._logs.LoggingHandler, not the instrumentation-layer one — check both.
    try:
        from opentelemetry.sdk._logs import LoggingHandler as _SDKLoggingHandler

        handler_types: tuple[type, ...] = (LoggingHandler, _SDKLoggingHandler)
    except ImportError:
        handler_types = (LoggingHandler,)
    return any(isinstance(h, handler_types) for h in logging.getLogger().handlers)


# Global meter provider
_meter_provider: Optional[MeterProvider] = None
_meter: Optional[metrics.Meter] = None

# Global logger provider
_log_provider: Optional[LoggerProvider] = None


def get_meter() -> metrics.Meter:
    """Get or create the global meter instance.

    Returns:
        Meter instance for creating metrics.
    """
    global _meter_provider, _meter

    if _meter is None:
        if _meter_provider is None:
            _meter_provider = _setup_meter_provider()

        if _meter_provider is not None:
            _meter = metrics.get_meter(SDK_PACKAGE_NAME, version=get_version())
        else:
            # Return a no-op meter if provider setup failed
            _meter = metrics.get_meter_provider().get_meter(SDK_PACKAGE_NAME)

    return _meter


def shutdown() -> None:
    """Shutdown the meter provider and flush any pending metrics."""
    global _meter_provider

    if _meter_provider is not None:
        try:
            _meter_provider.shutdown()
            logger.info("OpenTelemetry meter provider shutdown successfully")
        except Exception as e:
            logger.error(f"Error during OpenTelemetry meter provider shutdown: {e}")

        _meter_provider = None


def setup_log_provider() -> Optional[LoggerProvider]:
    """Set up the global OTel LoggerProvider using the shared resource attributes.

    Installs a LoggingHandler on the root stdlib logger so all existing
    logging.getLogger(...) calls in the app flow through OTel automatically.
    No-op when telemetry is disabled.
    """
    global _log_provider

    if _log_provider is not None:
        return _log_provider

    config = get_config()
    if not config.enabled:
        return None

    try:
        resource = Resource.create(create_resource_attributes_from_env())
        existing = cast(LoggerProvider, get_logger_provider())

        if isinstance(existing, LoggerProvider):
            # Never add a second BatchLogRecordProcessor — the platform's provider
            # already has one, and a second processor doubles every exported log record.
            logger.warning(
                "Global LoggerProvider was already set by another library. "
                "Merging sap.cloud_sdk.* resource attributes into the existing provider."
            )
            _merge_sdk_resource_into_log_provider(existing, resource)
            if not _root_logger_has_otel_handler():
                logging.getLogger().addHandler(LoggingHandler(logger_provider=existing))
            _log_provider = existing
        else:
            provider = LoggerProvider(resource=resource)
            provider.add_log_record_processor(
                BatchLogRecordProcessor(_create_log_exporter())
            )
            set_logger_provider(provider)
            logging.getLogger().addHandler(LoggingHandler(logger_provider=provider))
            _log_provider = provider

        logger.info(
            f"OpenTelemetry log provider initialized. "
            f"Service: {config.service_name}, "
            f"Endpoint: {config.otlp_endpoint}"
        )
        return _log_provider

    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry log provider: {e}")
        return None


def _create_log_exporter():
    protocol = os.getenv(ENV_OTLP_PROTOCOL, "grpc").lower()
    exporter_classes = {"grpc": GRPCLogExporter, "http/protobuf": HTTPLogExporter}

    if protocol not in exporter_classes:
        raise ValueError(
            f"Unsupported OTEL_EXPORTER_OTLP_PROTOCOL: '{protocol}'. "
            "Supported values are 'grpc' and 'http/protobuf'."
        )
    return exporter_classes[protocol]()


def _create_metric_exporter():
    protocol = os.getenv(ENV_OTLP_PROTOCOL, "grpc").lower()
    exporter_classes = {"grpc": GRPCMetricExporter, "http/protobuf": HTTPMetricExporter}

    if protocol not in exporter_classes:
        raise ValueError(
            f"Unsupported OTEL_EXPORTER_OTLP_PROTOCOL: '{protocol}'. "
            "Supported values are 'grpc' and 'http/protobuf'."
        )
    temporality: dict[type, AggregationTemporality] = {
        Counter: AggregationTemporality.DELTA,
        Histogram: AggregationTemporality.DELTA,
        ObservableCounter: AggregationTemporality.DELTA,
        ObservableGauge: AggregationTemporality.DELTA,
        ObservableUpDownCounter: AggregationTemporality.DELTA,
        UpDownCounter: AggregationTemporality.DELTA,
    }
    return exporter_classes[protocol](preferred_temporality=temporality)


def _setup_meter_provider() -> Optional[MeterProvider]:
    config = get_config()

    if not config.enabled:
        logger.debug("OpenTelemetry telemetry is disabled")
        return None

    try:
        resource = Resource.create(create_resource_attributes_from_env())
        exporter = _create_metric_exporter()
        reader = PeriodicExportingMetricReader(exporter=exporter)
        provider = MeterProvider(resource=resource, metric_readers=[reader])

        metrics.set_meter_provider(provider)
        logger.info(
            f"OpenTelemetry meter provider initialized. "
            f"Service: {config.service_name}, "
            f"Endpoint: {config.otlp_endpoint}"
        )

        return provider

    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry meter provider: {e}")
        return None
