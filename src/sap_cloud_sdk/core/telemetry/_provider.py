"""Internal module for setting up OpenTelemetry meter provider."""

import logging
from typing import Optional

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider, Counter
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource

from sap_cloud_sdk.core.telemetry.config import (
    get_config,
    create_resource_attributes_from_env,
)
from sap_cloud_sdk.core._version import get_version
from sap_cloud_sdk.core.telemetry.constants import SDK_PACKAGE_NAME

logger = logging.getLogger(__name__)

# Global meter provider
_meter_provider: Optional[MeterProvider] = None
_meter: Optional[metrics.Meter] = None


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


def _setup_meter_provider() -> Optional[MeterProvider]:
    """Set up the OpenTelemetry meter provider.

    Returns:
        MeterProvider instance if enabled, None if disabled.
    """
    config = get_config()

    if not config.enabled:
        logger.debug("OpenTelemetry telemetry is disabled")
        return None

    try:
        resource = Resource.create(create_resource_attributes_from_env())

        exporter = OTLPMetricExporter(
            endpoint=config.otlp_endpoint,
            preferred_temporality={
                Counter: AggregationTemporality.DELTA,
            },
        )

        # Create metric reader with periodic export
        reader = PeriodicExportingMetricReader(exporter=exporter)

        # Create and set meter provider
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
