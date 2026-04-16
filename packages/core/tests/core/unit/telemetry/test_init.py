"""Tests for telemetry module exports."""

from sap_cloud_sdk.telemetry import GenAIOperation, Module, Operation, add_span_attribute, context_overlay, get_current_span, record_error_metric, record_metrics, record_request_metric
import pytest


class TestTelemetryExports:
    """Test suite for telemetry module public API exports."""

    def test_module_exports(self):
        """Test that all public APIs are exported from __init__.py."""
        from sap_cloud_sdk import telemetry

        # Core functions
        assert hasattr(telemetry, 'record_request_metric')
        assert hasattr(telemetry, 'record_error_metric')

        # Types
        assert hasattr(telemetry, 'Module')
        assert hasattr(telemetry, 'Operation')
        assert hasattr(telemetry, 'GenAIOperation')

        # Decorator
        assert hasattr(telemetry, 'record_metrics')

        # Auto-instrumentation
        assert hasattr(telemetry, 'auto_instrument')

        # Tracer utilities
        assert hasattr(telemetry, 'context_overlay')
        assert hasattr(telemetry, 'get_current_span')
        assert hasattr(telemetry, 'add_span_attribute')

    def test_all_exports_in_all(self):
        """Test that __all__ contains expected exports."""
        from sap_cloud_sdk.telemetry import __all__

        expected_exports = [
            'Module',
            'Operation',
            'GenAIOperation',
            'record_metrics',
            'record_request_metric',
            'record_error_metric',
            'auto_instrument',
            'context_overlay',
            'get_current_span',
            'add_span_attribute',
        ]

        for export in expected_exports:
            assert export in __all__, f"{export} not in __all__"

    def test_imports_work(self):
        """Test that imports work correctly."""
        # Test direct imports
        from sap_cloud_sdk.telemetry import (
            auto_instrument,
        )

        # All should be callable or types
        assert callable(record_request_metric)
        assert callable(record_error_metric)
        assert callable(record_metrics)
        assert callable(auto_instrument)
        assert callable(context_overlay)
        assert callable(get_current_span)
        assert callable(add_span_attribute)

        # Enums
        assert hasattr(Module, 'AICORE')
        assert hasattr(Operation, 'AUDITLOG_LOG')
        assert hasattr(GenAIOperation, 'CHAT')

    def test_star_import(self):
        """Test that star import works correctly."""
        import sys
        import importlib

        # Create a temporary module for testing
        test_module = type(sys)('test_telemetry_import')

        # Execute star import in the test module's namespace
        exec('from sap_cloud_sdk.telemetry import *', test_module.__dict__)

        # Check expected exports are available
        assert 'Module' in test_module.__dict__
        assert 'Operation' in test_module.__dict__
        assert 'GenAIOperation' in test_module.__dict__
        assert 'record_metrics' in test_module.__dict__
        assert 'record_request_metric' in test_module.__dict__
        assert 'record_error_metric' in test_module.__dict__
        assert 'auto_instrument' in test_module.__dict__
        assert 'context_overlay' in test_module.__dict__
        assert 'get_current_span' in test_module.__dict__
        assert 'add_span_attribute' in test_module.__dict__

    def test_module_has_docstring(self):
        """Test that module has documentation."""
        from sap_cloud_sdk import telemetry

        assert telemetry.__doc__ is not None
        assert len(telemetry.__doc__) > 0
        assert 'OpenTelemetry' in telemetry.__doc__

    def test_no_private_exports(self):
        """Test that private names are not exported in __all__."""
        from sap_cloud_sdk.telemetry import __all__

        # __all__ should not contain private names (starting with _)
        for name in __all__:
            assert not name.startswith('_'), f"Private name {name} found in __all__"
