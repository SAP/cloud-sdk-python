"""Metrics decorator for telemetry with source detection from client instances."""

from functools import wraps
from typing import Callable, TypeVar, ParamSpec

from cloud_sdk_python.core.telemetry import Module, record_request_metric, record_error_metric

P = ParamSpec('P')
R = TypeVar('R')


def record_metrics(module: Module, operation: str, deprecated: bool = False) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to automatically record request and error metrics for SDK operations.

    This decorator wraps SDK methods to automatically emit OpenTelemetry metrics
    for successful requests and errors. It's specifically designed for metrics
    instrumentation and should not be confused with general instrumentation or tracing.
    
    The decorator automatically detects the source of the call by checking the
    `_telemetry_source` property on the client instance (self):
    - If the client has `_telemetry_source` set, it means it was created by another
      SDK module (e.g., objectstore → auditlog), and that module becomes the source
    - If `_telemetry_source` is None or not present, the call is from user code
      and the source will be None (which represents "user-facing")

    Args:
        module: The module name (e.g., Module.DESTINATION)
        operation: The operation name (e.g., "get_instance_destination", "create_destination")
        deprecated: Whether the operation is deprecated (default: False)
    
    Returns:
        Decorated function that records request/error metrics with automatic source detection.
    
    Example:
        ```python
        from cloud_sdk_python.core.telemetry import record_metrics, Module, Operation
        
        class DestinationClient:
            def __init__(self):
                # _telemetry_source is set by create_client() when created internally
                self._telemetry_source = None  # or Module.OBJECTSTORE if created by objectstore
            
            @record_metrics(Module.DESTINATION, Operation.DESTINATION_GET_INSTANCE_DESTINATION)
            def get_instance_destination(self, name: str):
                # Metrics automatically recorded with source from self._telemetry_source
                pass
        ```
    
    Note:
        This decorator is specifically for metrics. Future instrumentation needs
        (e.g., distributed tracing, logging) should use separate decorators to
        maintain clear separation of concerns.
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Extract source from the client instance (self is the first argument)
            source = None
            if args and hasattr(args[0], '_telemetry_source'):
                source = args[0]._telemetry_source
            
            try:
                result = func(*args, **kwargs)
                record_request_metric(
                    module,
                    source,
                    operation,
                    deprecated
                )
                return result
                
            except Exception:
                record_error_metric(
                    module,
                    source,
                    operation,
                    deprecated
                )
                raise
        
        return wrapper
    return decorator
