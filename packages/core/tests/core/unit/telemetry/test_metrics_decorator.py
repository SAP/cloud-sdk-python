"""Tests for metrics decorator implementation."""

import pytest
from unittest.mock import patch

from sap_cloud_sdk.telemetry.metrics_decorator import record_metrics
from sap_cloud_sdk.telemetry.module import Module
from sap_cloud_sdk.telemetry.operation import Operation


class TestRecordMetricsDecorator:
    """Test suite for @record_metrics decorator."""

    def test_decorator_executes_function_successfully(self):
        """Test that decorator allows function to execute normally."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = None

            @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
            def test_method(self):
                return "success"

        client = TestClient()
        result = client.test_method()

        assert result == "success"

    def test_decorator_reads_source_from_self_when_none(self):
        """Test that decorator reads _telemetry_source from self when it's None."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = None

            @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
            def test_method(self):
                return "called"

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric') as mock_metric:
            client.test_method()

            # Verify it was called with None as source
            mock_metric.assert_called_once_with(
                Module.AUDITLOG,
                None,  # source should be None
                Operation.AUDITLOG_LOG,
                False  # deprecated parameter
            )

    def test_decorator_reads_source_from_self_when_module_set(self):
        """Test that decorator reads _telemetry_source from self when it's a Module."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = Module.OBJECTSTORE

            @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
            def test_method(self):
                return "called"

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric') as mock_metric:
            client.test_method()

            # Verify it was called with Module.OBJECTSTORE as source
            mock_metric.assert_called_once_with(
                Module.AUDITLOG,
                Module.OBJECTSTORE,
                Operation.AUDITLOG_LOG,
                False  # deprecated parameter
            )

    def test_decorator_handles_missing_telemetry_source_attribute(self):
        """Test that decorator handles clients without _telemetry_source attribute."""

        class TestClient:
            # No _telemetry_source attribute

            @record_metrics(Module.DESTINATION, Operation.DESTINATION_GET_INSTANCE_DESTINATION)
            def test_method(self):
                return "called"

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric') as mock_metric:
            result = client.test_method()

            assert result == "called"
            # Should be called with None as source
            mock_metric.assert_called_once_with(
                Module.DESTINATION,
                None,
                Operation.DESTINATION_GET_INSTANCE_DESTINATION,
                False  # deprecated parameter
            )

    def test_decorator_records_error_metric_on_exception(self):
        """Test that decorator records error metric when function raises exception."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = None

            @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
            def failing_method(self):
                raise ValueError("Test error")

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_error_metric') as mock_error:
            with pytest.raises(ValueError, match="Test error"):
                client.failing_method()

            # Verify error metric was recorded
            mock_error.assert_called_once_with(
                Module.AUDITLOG,
                None,
                Operation.AUDITLOG_LOG,
                False  # deprecated parameter
            )

    def test_decorator_records_error_metric_with_source_on_exception(self):
        """Test that decorator records error metric with source when function raises exception."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = Module.OBJECTSTORE

            @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
            def failing_method(self):
                raise RuntimeError("Test error")

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_error_metric') as mock_error:
            with pytest.raises(RuntimeError, match="Test error"):
                client.failing_method()

            # Verify error metric was recorded with source
            mock_error.assert_called_once_with(
                Module.AUDITLOG,
                Module.OBJECTSTORE,
                Operation.AUDITLOG_LOG,
                False  # deprecated parameter
            )

    def test_decorator_propagates_exceptions(self):
        """Test that decorator propagates exceptions from decorated function."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = None

            @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
            def failing_method(self):
                raise ValueError("Original error")

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_error_metric'):
            with pytest.raises(ValueError, match="Original error"):
                client.failing_method()

    def test_decorator_preserves_function_return_value(self):
        """Test that decorator returns the original function's return value."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = None

            @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_PUT_OBJECT)
            def method_with_return(self):
                return {"status": "uploaded", "size": 1024}

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric'):
            result = client.method_with_return()

            assert result == {"status": "uploaded", "size": 1024}

    def test_decorator_works_with_multiple_parameters(self):
        """Test that decorator works with functions that have multiple parameters."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = None

            @record_metrics(Module.DESTINATION, Operation.DESTINATION_CREATE_DESTINATION)
            def method_with_params(self, name, config, level=None):
                return f"{name}-{config}-{level}"

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric'):
            result = client.method_with_params("dest", "prod", level="subaccount")

            assert result == "dest-prod-subaccount"

    def test_decorator_works_with_kwargs(self):
        """Test that decorator works with keyword arguments."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = Module.OBJECTSTORE

            @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG_BATCH)
            def method_with_kwargs(self, **kwargs):
                return kwargs

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric'):
            result = client.method_with_kwargs(events=[1, 2, 3], batch_size=10)

            assert result == {"events": [1, 2, 3], "batch_size": 10}

    def test_decorator_records_metric_before_returning(self):
        """Test that decorator records metric after function execution but before return."""

        execution_order = []

        class TestClient:
            def __init__(self):
                self._telemetry_source = None

            @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
            def test_method(self):
                execution_order.append("function")
                return "done"

        client = TestClient()

        def mock_record(*args):
            execution_order.append("metric")

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric', side_effect=mock_record):
            client.test_method()

            assert execution_order == ["function", "metric"]

    def test_decorator_uses_correct_module_and_operation(self):
        """Test that decorator passes correct module and operation to metric recording."""

        class TestClient:
            def __init__(self):
                self._telemetry_source = None

            @record_metrics(Module.OBJECTSTORE, Operation.OBJECTSTORE_DELETE_OBJECT)
            def delete_operation(self):
                return True

        client = TestClient()

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric') as mock_metric:
            client.delete_operation()

            call_args = mock_metric.call_args[0]
            assert call_args[0] == Module.OBJECTSTORE
            assert call_args[2] == Operation.OBJECTSTORE_DELETE_OBJECT

    def test_decorator_handles_different_source_values(self):
        """Test decorator with various _telemetry_source values."""

        test_cases = [
            (None, None),
            (Module.OBJECTSTORE, Module.OBJECTSTORE),
            (Module.DESTINATION, Module.DESTINATION),
        ]

        for source_value, expected_source in test_cases:
            class TestClient:
                def __init__(self, source):
                    self._telemetry_source = source

                @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
                def test_method(self):
                    return "called"

            client = TestClient(source_value)

            with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric') as mock_metric:
                client.test_method()

                call_args = mock_metric.call_args[0]
                assert call_args[1] == expected_source

    def test_decorator_on_static_method_uses_none_source(self):
        """Test that decorator on static/class methods uses None as source."""

        class TestClient:
            @staticmethod
            @record_metrics(Module.AUDITLOG, Operation.AUDITLOG_LOG)
            def static_method():
                return "static"

        with patch('sap_cloud_sdk.telemetry.metrics_decorator.record_request_metric') as mock_metric:
            result = TestClient.static_method()

            assert result == "static"
            # Should use None for source since there's no self
            call_args = mock_metric.call_args[0]
            assert call_args[1] is None
