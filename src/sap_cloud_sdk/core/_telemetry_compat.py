"""Conditional telemetry imports for modules that use telemetry as optional dependency.

This module provides a centralized way to handle optional telemetry dependencies.
When telemetry packages are not installed, it provides no-op implementations.
"""

from typing import Any, Callable, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])

try:
    from sap_cloud_sdk.core.telemetry import Module, Operation, record_metrics
    TELEMETRY_AVAILABLE = True
except ImportError:
    # Telemetry packages not installed — provide no-op implementations
    TELEMETRY_AVAILABLE = False
    Module = None  # type: ignore
    Operation = None  # type: ignore

    def record_metrics(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        """No-op decorator when telemetry is not available."""
        def decorator(func: _F) -> _F:
            return func
        if args and callable(args[0]):
            # Called without parentheses: @record_metrics
            return args[0]
        # Called with parentheses: @record_metrics(...)
        return decorator


__all__ = ["Module", "Operation", "record_metrics", "TELEMETRY_AVAILABLE"]
