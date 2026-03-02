"""OpenTelemetry telemetry for Cloud SDK.

This module provides functions to record telemetry metrics for SDK operations,
"""

import logging
from contextvars import ContextVar
from typing import Optional, Dict, Any

from opentelemetry import metrics

from cloud_sdk_python.core.telemetry._provider import get_meter
from cloud_sdk_python.core.telemetry.constants import (
    REQUEST_COUNTER_NAME,
    ERROR_COUNTER_NAME,
    LLM_TOKEN_HISTOGRAM_NAME,
    ATTR_SAP_TENANT_ID,
    ATTR_CAPABILITY,
    ATTR_FUNCTIONALITY,
    ATTR_SOURCE,
    ATTR_DEPRECATED,
    ATTR_GENAI_REQUEST_MODEL,
    ATTR_GENAI_OPERATION_NAME,
    ATTR_GENAI_TOKEN_TYPE,
    ATTR_GENAI_PROVIDER,
)
from cloud_sdk_python.core.telemetry.module import Module

logger = logging.getLogger(__name__)


# Global metric instruments
_request_counter: Optional[metrics.Counter] = None
_error_counter: Optional[metrics.Counter] = None
_aicore_token_histogram: Optional[metrics.Histogram] = None

# Context variable for per-request tenant ID
_tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")

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
        from cloud_sdk_python.core.telemetry import set_tenant_id
        
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


def record_request_metric(
    module: Module,
    source: Optional[Module],
    operation: str,
    deprecated: bool = False
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
    module: Module,
    source: Optional[Module],
    operation: str,
    deprecated: bool = False
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


def record_aicore_metric(
    model_name: str,
    provider: str,
    operation_name: str,
    input_tokens: int,
    output_tokens: int,
    custom_attributes: Optional[Dict[str, Any]] = None
) -> None:
    """Record token usage metrics for GenAI model API calls.
    
    This function records token consumption for Generative AI model API calls following
    OpenTelemetry GenAI semantic conventions. It creates two separate histogram observations:
    one for input tokens and one for output tokens, each differentiated by the gen_ai.token.type
    attribute. The metrics include all default SDK attributes (service instance, SDK version,
    deployment metadata, etc.) along with the model name.

    Args:
        model_name: The name of the GenAI model (e.g., "gpt-4", "claude-3-opus")
        provider: The name of the GenAI provider (e.g., "openai", "anthropic", "sap-aicore")
        operation_name: The type of GenAI operation. Well-known values include:
            - "chat": Chat completion operation (e.g., OpenAI Chat API)
            - "text_completion": Text completion operation
            - "embeddings": Embeddings operation (e.g., OpenAI Create embeddings API)
            - "generate_content": Multimodal content generation (e.g., Gemini Generate Content)
            - "create_agent": Create GenAI agent
            - "invoke_agent": Invoke GenAI agent
            - "execute_tool": Execute a tool
            Custom values are also allowed.
        input_tokens: Number of input/prompt tokens consumed
        output_tokens: Number of output/completion tokens generated
        custom_attributes: Optional dictionary of additional custom attributes to include
            in the metric. These will be merged with the standard attributes.
    
    Example:
        ```python
        from cloud_sdk_python.core.telemetry import record_aicore_metric
        
        # Chat completion
        record_aicore_metric(
            model_name="gpt-4",
            provider="openai",
            operation_name="chat",
            input_tokens=150,
            output_tokens=75
        )
        
        # With additional custom attributes
        record_aicore_metric(
            model_name="gpt-4",
            provider="openai",
            operation_name="chat",
            input_tokens=150,
            output_tokens=75,
            custom_attributes={
                "user_id": "user123",
                "session_id": "session456"
            }
        )
        ```
    """
    global _aicore_token_histogram
    
    # Lazy initialization of metrics
    if _aicore_token_histogram is None:
        _initialize_aicore_metrics()
    if _aicore_token_histogram is None:
        return
    
    try:
        base_attributes = _genai_base_attributes(model_name, provider, operation_name)
        
        # Merge in any additional user-provided attributes
        if custom_attributes:
            base_attributes.update(custom_attributes)
        
        # Record input tokens as separate histogram observation
        input_attributes = base_attributes.copy()
        input_attributes[ATTR_GENAI_TOKEN_TYPE] = "input"
        _aicore_token_histogram.record(input_tokens, input_attributes)
        
        # Record output tokens as separate histogram observation
        output_attributes = base_attributes.copy()
        output_attributes[ATTR_GENAI_TOKEN_TYPE] = "output"
        _aicore_token_histogram.record(output_tokens, output_attributes)
        
    except Exception as e:
        logger.debug(f"Failed to record GenAI metric: {e}")


def _genai_base_attributes(model_name: str, provider: str, operation_name: str) -> Dict[str, Any]:
    """Get base attributes for GenAI metrics.

    Args:
        model_name: The name of the LLM model
        provider: The name of the GenAI provider
        operation_name: The type of GenAI operation

    Returns:
        Dictionary of attributes with default SDK attributes plus GenAI-specific ones.
    """
    # Start with default SDK attributes for AI Core module
    attributes = default_attributes(
        module=Module.AICORE,
        source=None,
        operation="model_call",
        deprecated=False
    )

    # Add GenAI-specific attributes
    attributes[ATTR_GENAI_REQUEST_MODEL] = model_name
    attributes[ATTR_GENAI_PROVIDER] = provider
    attributes[ATTR_GENAI_OPERATION_NAME] = operation_name

    return attributes

def _initialize_aicore_metrics() -> None:
    """Initialize GenAI-specific metric instruments."""
    global _aicore_token_histogram

    try:
        meter = get_meter()

        # GenAI token usage histogram
        _aicore_token_histogram = meter.create_histogram(
            name=LLM_TOKEN_HISTOGRAM_NAME,
            description="Token usage for GenAI model requests",
            unit="{tokens}"
        )

        logger.debug("GenAI telemetry metrics initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize GenAI telemetry metrics: {e}")


def default_attributes(
        module: Module,
        source: Optional[Module],
        operation: str,
        deprecated: bool = False
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
            unit="{requests}"
        )

        # New errors counter meter
        _error_counter = meter.create_counter(
            name=ERROR_COUNTER_NAME,
            description="Number of errors encountered for a specific capability functionality",
            unit="{errors}"
        )

        logger.debug("Telemetry metrics initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize telemetry metrics: {e}")
