"""OpenTelemetry telemetry for Cloud SDK.

This module provides functions to record telemetry metrics for SDK operations,
"""

import logging
from contextvars import ContextVar
from typing import Any, Dict, Optional

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

# Context variable for per-request tenant ID
_tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")

# Context variable for propagated span attributes
_propagated_attrs_var: ContextVar[Dict[str, Any]] = ContextVar(
    "propagated_attrs", default={}
)

# In-process identity for invoke_agent_span(propagate=True) — injected via SpanProcessor
_invoke_agent_identity_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "sap_cloud_sdk_invoke_agent_identity", default=None
)


def get_invoke_agent_identity() -> Optional[Dict[str, Any]]:
    """Return merged ``gen_ai.agent.*`` attributes for the current invoke_agent propagation scope."""
    return _invoke_agent_identity_var.get()


def set_tenant_id(tenant_id: str) -> None:
    """Set the tenant ID for the current request context.

    This function sets the tenant ID that will be included in all telemetry
    metrics and spans for the current request. The tenant ID is stored in a
    context variable, making it thread-safe and async-safe.

    Args:
        tenant_id: The tenant identifier to set for the current request context.
            Use an empty string to clear the tenant ID.

    Example:
        ```python
        from sap_cloud_sdk.core.telemetry import set_tenant_id

        # In middleware or request handler
        def handle_request(request):
            tenant_id = extract_tenant_from_jwt(request)
            set_tenant_id(tenant_id)

            # All SDK operations in this request will include this tenant ID
            destination = destination_client.get_destination("my-dest")
            # The metric recorded will have sap.tenancy.tenant_id = tenant_id
        ```

    Note:
        The tenant ID is automatically propagated to child contexts (spans, async tasks)
        thanks to Python's contextvars mechanism. You only need to set it once at the
        request entry point.
    """
    _tenant_id_var.set(tenant_id)


def get_tenant_id() -> str:
    """Get the tenant ID from the current request context.

    Returns:
        The tenant ID for the current request context, or an empty string if not set.

    Note:
        This function is primarily for internal use. Users should use set_tenant_id()
        to set the tenant ID at the request entry point.
    """
    return _tenant_id_var.get()


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

    # Lazy initialization of metrics
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

    # Lazy initialization of metrics
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
    return {
        # Per-request/operation attributes (vary between operations)
        ATTR_SAP_TENANT_ID: get_tenant_id(),  # Per-request tenant ID
        ATTR_CAPABILITY: str(module),  # Varies by SDK module
        ATTR_FUNCTIONALITY: operation,  # Varies by operation
        ATTR_SOURCE: str(source) if source else "user-facing",  # Varies by call source
        ATTR_DEPRECATED: deprecated,  # Varies by operation
    }


def _initialize_metrics() -> None:
    """Initialize global metric instruments."""
    global _request_counter, _error_counter

    try:
        meter = get_meter()

        # New requests counter meter
        _request_counter = meter.create_counter(
            name=REQUEST_COUNTER_NAME,
            description="Number of requests to a specific capability functionality",
            unit="{requests}",
        )

        # New errors counter meter
        _error_counter = meter.create_counter(
            name=ERROR_COUNTER_NAME,
            description="Number of errors encountered for a specific capability functionality",
            unit="{errors}",
        )

        logger.debug("Telemetry metrics initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize telemetry metrics: {e}")
