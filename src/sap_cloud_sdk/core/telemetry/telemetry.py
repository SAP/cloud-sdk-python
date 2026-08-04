"""OpenTelemetry telemetry for Cloud SDK.

This module provides functions to record telemetry metrics for SDK operations,
"""

import logging
from contextvars import ContextVar
from typing import Optional, Dict, Any

from opentelemetry import metrics

from sap_cloud_sdk.core.telemetry._provider import get_meter
from sap_cloud_sdk.core.telemetry.constants import (
    REQUEST_COUNTER_NAME,
    ERROR_COUNTER_NAME,
    ATTR_SAP_TENANT_ID,
    ATTR_CAPABILITY,
    ATTR_FUNCTIONALITY,
    ATTR_SOURCE,
    ATTR_DEPRECATED,
)
from sap_cloud_sdk.core.telemetry.module import Module

logger = logging.getLogger(__name__)


# Global metric instruments
_request_counter: Optional[metrics.Counter] = None
_error_counter: Optional[metrics.Counter] = None

# Context variable for propagated span attributes
_propagated_attrs_var: ContextVar[Dict[str, Any]] = ContextVar(
    "propagated_attrs", default={}
)


def get_propagated_attributes() -> Dict[str, Any]:
    """Get the propagated span attributes from the current context.

    Returns:
        Dict of attributes propagated from an ancestor span with propagate=True,
        or an empty dict if none are set.
    """
    return _propagated_attrs_var.get()


def record_request_metric(
    module: Module, source: Optional[Module], operation: str, deprecated: bool = False
) -> None:
    """Record a request metric for an SDK operation.

    Args:
        module: The SDK module (e.g., Module.AUDITLOG)
        source: The source from the method call
        operation: The operation name (e.g., "log", "get_destination")
        deprecated: Whether the operation is deprecated
    """
    global _request_counter

    if _request_counter is None:
        _initialize_metrics()
    if _request_counter is None:
        return

    try:
        attributes = default_attributes(module, source, operation, deprecated)
        _request_counter.add(1, attributes)
    except Exception as e:
        logger.debug(f"Failed to record request metric: {e}")


def record_error_metric(
    module: Module, source: Optional[Module], operation: str, deprecated: bool = False
) -> None:
    """Record an error metric for an SDK operation.

    Args:
        module: The SDK module (e.g., Module.AUDITLOG)
        source: The source from the method call
        operation: The operation name (e.g., "log", "get_destination")
        deprecated: Whether the operation is deprecated
    """
    global _error_counter

    if _error_counter is None:
        _initialize_metrics()
    if _error_counter is None:
        return

    try:
        attributes = default_attributes(module, source, operation, deprecated)
        _error_counter.add(1, attributes)
    except Exception as e:
        logger.debug(f"Failed to record error metric: {e}")


def default_attributes(
    module: Module, source: Optional[Module], operation: str, deprecated: bool = False
) -> Dict[str, Any]:
    """Get default attributes for an SDK operation.

    Returns only per-operation attributes. Static attributes (service name, SDK version, etc.)
    are set once in resource attributes and automatically propagated to all spans/metrics.

    Args:
        module: The SDK module (e.g., Module.AUDITLOG)
        source: The source from the method call
        operation: The operation name (e.g., "log", "get_destination")
        deprecated: Whether the operation is deprecated

    Returns:
        Dictionary of per-operation attributes (not resource attributes).
    """
    from sap_cloud_sdk.core.runtime_context._context import get_context
    from sap_cloud_sdk.core.runtime_context.providers._ias import GLOBAL_TENANT_ID

    tenant_id = get_context().get(GLOBAL_TENANT_ID) or ""
    return {
        ATTR_SAP_TENANT_ID: tenant_id,
        ATTR_CAPABILITY: str(module),
        ATTR_FUNCTIONALITY: operation,
        ATTR_SOURCE: str(source) if source else "user-facing",
        ATTR_DEPRECATED: deprecated,
    }


def _initialize_metrics() -> None:
    """Initialize global metric instruments."""
    global _request_counter, _error_counter

    try:
        meter = get_meter()

        _request_counter = meter.create_counter(
            name=REQUEST_COUNTER_NAME,
            description="Number of requests to a specific capability functionality",
            unit="{requests}",
        )

        _error_counter = meter.create_counter(
            name=ERROR_COUNTER_NAME,
            description="Number of errors encountered for a specific capability functionality",
            unit="{errors}",
        )

        logger.debug("Telemetry metrics initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize telemetry metrics: {e}")

