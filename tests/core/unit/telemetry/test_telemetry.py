"""Tests for core telemetry functionality."""

from unittest.mock import patch, MagicMock

from sap_cloud_sdk.core.telemetry.config import (
    _get_region,
    _get_environment,
    _get_subaccount_id,
    _get_app_name,
    _get_hostname,
    DEFAULT_UNKNOWN,
)
from sap_cloud_sdk.core.telemetry.constants import (
    ATTR_SERVICE_INSTANCE_ID,
    ATTR_SERVICE_NAME,
    ATTR_DEPLOYMENT_ENVIRONMENT,
    ATTR_CLOUD_REGION,
    ATTR_SAP_SUBACCOUNT_ID,
    ATTR_SAP_SDK_LANGUAGE,
    ATTR_SAP_SDK_VERSION,
    ATTR_CAPABILITY,
    ATTR_FUNCTIONALITY,
    ATTR_SOURCE,
    ATTR_DEPRECATED,
    ATTR_SAP_TENANT_ID,
)
from sap_cloud_sdk.core.telemetry.module import Module
from sap_cloud_sdk.core.telemetry.telemetry import (
    record_request_metric,
    record_error_metric,
    default_attributes,
)


class TestEnvironmentHelpers:
    """Test suite for environment variable helper functions."""

    def test_get_region_with_value(self):
        """Test getting region from environment."""
        with patch.dict('os.environ', {'APPFND_CONHOS_REGION': 'eu10'}, clear=True):
            assert _get_region() == 'eu10'

    def test_get_region_default(self):
        """Test getting region default when not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert _get_region() == DEFAULT_UNKNOWN

    def test_get_environment_with_value(self):
        """Test getting environment from environment."""
        with patch.dict('os.environ', {'APPFND_CONHOS_ENVIRONMENT': 'prod'}, clear=True):
            assert _get_environment() == 'prod'

    def test_get_environment_default(self):
        """Test getting environment default when not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert _get_environment() == DEFAULT_UNKNOWN

    def test_get_subaccount_id_with_value(self):
        """Test getting subaccount ID from environment."""
        with patch.dict('os.environ', {'APPFND_CONHOS_SUBACCOUNTID': 'sub-123'}, clear=True):
            assert _get_subaccount_id() == 'sub-123'

    def test_get_subaccount_id_default(self):
        """Test getting subaccount ID default when not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert _get_subaccount_id() == DEFAULT_UNKNOWN

    def test_get_app_name_with_value(self):
        """Test getting app name from environment."""
        with patch.dict('os.environ', {'APPFND_CONHOS_APP_NAME': 'my-app'}, clear=True):
            assert _get_app_name() == 'my-app'

    def test_get_app_name_falls_back_to_otel_service_name(self):
        """Test that OTEL_SERVICE_NAME is used when APPFND_CONHOS_APP_NAME is not set."""
        with patch.dict('os.environ', {'OTEL_SERVICE_NAME': 'my-agent'}, clear=True):
            assert _get_app_name() == 'my-agent'

    def test_get_app_name_prefers_appfnd_over_otel(self):
        """Test that APPFND_CONHOS_APP_NAME takes precedence over OTEL_SERVICE_NAME."""
        with patch.dict('os.environ', {'APPFND_CONHOS_APP_NAME': 'appfnd-name', 'OTEL_SERVICE_NAME': 'otel-name'}, clear=True):
            assert _get_app_name() == 'appfnd-name'

    def test_get_app_name_default(self):
        """Test getting app name default when not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert _get_app_name() == DEFAULT_UNKNOWN

    def test_get_hostname_with_value(self):
        """Test getting hostname from environment."""
        with patch.dict('os.environ', {'HOSTNAME': 'server-01'}, clear=True):
            assert _get_hostname() == 'server-01'

    def test_get_hostname_default(self):
        """Test getting hostname default when not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert _get_hostname() == DEFAULT_UNKNOWN


class TestDefaultAttributes:
    """Test suite for default_attributes function."""

    def test_default_attributes_basic(self):
        """Test default attributes with basic parameters."""
        with patch.dict('os.environ', {}, clear=True):
            attrs = default_attributes(
                module=Module.AUDITLOG,
                source=None,
                operation="log",
                deprecated=False
            )

            assert attrs[ATTR_CAPABILITY] == str(Module.AUDITLOG)
            assert attrs[ATTR_FUNCTIONALITY] == "log"
            assert attrs[ATTR_SOURCE] == "user-facing"
            assert attrs[ATTR_DEPRECATED] is False
            assert attrs[ATTR_SAP_TENANT_ID] == ""  # Empty by default

    def test_default_attributes_with_source(self):
        """Test default attributes with a source module."""
        attrs = default_attributes(
            module=Module.AUDITLOG,
            source=Module.OBJECTSTORE,
            operation="log",
            deprecated=False
        )

        assert attrs[ATTR_SOURCE] == str(Module.OBJECTSTORE)

    def test_default_attributes_deprecated_true(self):
        """Test default attributes with deprecated flag."""
        attrs = default_attributes(
            module=Module.DESTINATION,
            source=None,
            operation="get_destination",
            deprecated=True
        )

        assert attrs[ATTR_DEPRECATED] is True



class TestRecordRequestMetric:
    """Test suite for record_request_metric function."""

    def test_record_request_metric_basic(self):
        """Test recording a basic request metric."""
        import sap_cloud_sdk.core.telemetry.telemetry as telemetry_module

        mock_counter = MagicMock()
        telemetry_module._request_counter = mock_counter

        record_request_metric(
            module=Module.AUDITLOG,
            source=None,
            operation="log",
            deprecated=False
        )

        mock_counter.add.assert_called_once()
        call_args = mock_counter.add.call_args
        assert call_args[0][0] == 1  # Count should be 1
        attrs = call_args[0][1]
        assert attrs[ATTR_CAPABILITY] == str(Module.AUDITLOG)
        assert attrs[ATTR_FUNCTIONALITY] == "log"

    def test_record_request_metric_with_source(self):
        """Test recording request metric with source."""
        import sap_cloud_sdk.core.telemetry.telemetry as telemetry_module

        mock_counter = MagicMock()
        telemetry_module._request_counter = mock_counter

        record_request_metric(
            module=Module.DESTINATION,
            source=Module.OBJECTSTORE,
            operation="get_instance_destination",
            deprecated=False
        )

        mock_counter.add.assert_called_once()
        call_args = mock_counter.add.call_args
        attrs = call_args[0][1]
        assert attrs[ATTR_SOURCE] == str(Module.OBJECTSTORE)

    def test_record_request_metric_lazy_initialization(self):
        """Test that request metric initializes counter lazily."""
        import sap_cloud_sdk.core.telemetry.telemetry as telemetry_module

        # Reset counter to None to trigger initialization
        telemetry_module._request_counter = None

        with patch('sap_cloud_sdk.core.telemetry.telemetry._initialize_metrics') as mock_init:
            mock_counter = MagicMock()

            def set_counter():
                telemetry_module._request_counter = mock_counter

            mock_init.side_effect = set_counter

            record_request_metric(
                module=Module.AUDITLOG,
                source=None,
                operation="log"
            )

            mock_init.assert_called_once()
            mock_counter.add.assert_called_once()

    def test_record_request_metric_handles_exception(self):
        """Test that request metric handles exceptions gracefully."""
        import sap_cloud_sdk.core.telemetry.telemetry as telemetry_module

        mock_counter = MagicMock()
        mock_counter.add.side_effect = Exception("Test error")
        telemetry_module._request_counter = mock_counter

        # Should not raise exception
        record_request_metric(
            module=Module.AUDITLOG,
            source=None,
            operation="log"
        )

    def test_record_request_metric_returns_early_if_counter_none(self):
        """Test that function returns early if counter initialization fails."""
        import sap_cloud_sdk.core.telemetry.telemetry as telemetry_module

        telemetry_module._request_counter = None

        with patch('sap_cloud_sdk.core.telemetry.telemetry._initialize_metrics'):
            # Counter remains None after initialization
            record_request_metric(
                module=Module.AUDITLOG,
                source=None,
                operation="log"
            )
            # Should complete without error


class TestRecordErrorMetric:
    """Test suite for record_error_metric function."""

    def test_record_error_metric_basic(self):
        """Test recording a basic error metric."""
        import sap_cloud_sdk.core.telemetry.telemetry as telemetry_module

        mock_counter = MagicMock()
        telemetry_module._error_counter = mock_counter

        record_error_metric(
            module=Module.AUDITLOG,
            source=None,
            operation="log",
            deprecated=False
        )

        mock_counter.add.assert_called_once()
        call_args = mock_counter.add.call_args
        assert call_args[0][0] == 1
        attrs = call_args[0][1]
        assert attrs[ATTR_CAPABILITY] == str(Module.AUDITLOG)
        assert attrs[ATTR_FUNCTIONALITY] == "log"

    def test_record_error_metric_with_source(self):
        """Test recording error metric with source."""
        import sap_cloud_sdk.core.telemetry.telemetry as telemetry_module

        mock_counter = MagicMock()
        telemetry_module._error_counter = mock_counter

        record_error_metric(
            module=Module.DESTINATION,
            source=Module.AUDITLOG,
            operation="get_destination",
            deprecated=True
        )

        mock_counter.add.assert_called_once()
        call_args = mock_counter.add.call_args
        attrs = call_args[0][1]
        assert attrs[ATTR_SOURCE] == str(Module.AUDITLOG)
        assert attrs[ATTR_DEPRECATED] is True

    def test_record_error_metric_lazy_initialization(self):
        """Test that error metric initializes counter lazily."""
        import sap_cloud_sdk.core.telemetry.telemetry as telemetry_module

        telemetry_module._error_counter = None

        with patch('sap_cloud_sdk.core.telemetry.telemetry._initialize_metrics') as mock_init:
            mock_counter = MagicMock()

            def set_counter():
                telemetry_module._error_counter = mock_counter

            mock_init.side_effect = set_counter

            record_error_metric(
                module=Module.OBJECTSTORE,
                source=None,
                operation="put_object"
            )

            mock_init.assert_called_once()
            mock_counter.add.assert_called_once()

    def test_record_error_metric_handles_exception(self):
        """Test that error metric handles exceptions gracefully."""
        import sap_cloud_sdk.core.telemetry.telemetry as telemetry_module

        mock_counter = MagicMock()
        mock_counter.add.side_effect = Exception("Test error")
        telemetry_module._error_counter = mock_counter

        # Should not raise exception
        record_error_metric(
            module=Module.DESTINATION,
            source=None,
            operation="create_destination"
        )
