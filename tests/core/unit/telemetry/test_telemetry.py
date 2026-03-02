"""Tests for core telemetry functionality."""

from unittest.mock import patch, MagicMock

from cloud_sdk_python.core.telemetry.config import (
    _get_conhos_region,
    _get_conhos_environment,
    _get_conhos_subaccount_id,
    _get_conhos_app_name,
    _get_hostname,
    DEFAULT_UNKNOWN,
)
from cloud_sdk_python.core.telemetry.constants import (
    LLM_TOKEN_HISTOGRAM_NAME,
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
    ATTR_GENAI_REQUEST_MODEL,
    ATTR_GENAI_PROVIDER,
    ATTR_GENAI_OPERATION_NAME,
    ATTR_GENAI_TOKEN_TYPE, ATTR_SAP_TENANT_ID,
)
from cloud_sdk_python.core.telemetry.module import Module
from cloud_sdk_python.core.telemetry.telemetry import (
    record_request_metric,
    record_error_metric,
    record_aicore_metric,
    default_attributes,
    _initialize_aicore_metrics,
    _genai_base_attributes,
)


class TestEnvironmentHelpers:
    """Test suite for environment variable helper functions."""

    def test_get_conhos_region_with_value(self):
        """Test getting ConHost region from environment."""
        with patch.dict('os.environ', {'APPFND_CONHOS_REGION': 'eu10'}, clear=True):
            assert _get_conhos_region() == 'eu10'

    def test_get_conhos_region_default(self):
        """Test getting ConHost region default when not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert _get_conhos_region() == DEFAULT_UNKNOWN

    def test_get_conhos_environment_with_value(self):
        """Test getting ConHost environment from environment."""
        with patch.dict('os.environ', {'APPFND_CONHOS_ENVIRONMENT': 'prod'}, clear=True):
            assert _get_conhos_environment() == 'prod'

    def test_get_conhos_environment_default(self):
        """Test getting ConHost environment default when not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert _get_conhos_environment() == DEFAULT_UNKNOWN

    def test_get_conhos_subaccount_id_with_value(self):
        """Test getting ConHost subaccount ID from environment."""
        with patch.dict('os.environ', {'APPFND_CONHOS_SUBACCOUNTID': 'sub-123'}, clear=True):
            assert _get_conhos_subaccount_id() == 'sub-123'

    def test_get_conhos_subaccount_id_default(self):
        """Test getting ConHost subaccount ID default when not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert _get_conhos_subaccount_id() == DEFAULT_UNKNOWN

    def test_get_conhos_app_name_with_value(self):
        """Test getting ConHost app name from environment."""
        with patch.dict('os.environ', {'APPFND_CONHOS_APP_NAME': 'my-app'}, clear=True):
            assert _get_conhos_app_name() == 'my-app'

    def test_get_conhos_app_name_default(self):
        """Test getting ConHost app name default when not set."""
        with patch.dict('os.environ', {}, clear=True):
            assert _get_conhos_app_name() == DEFAULT_UNKNOWN

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



class TestGenAIAttributes:
    """Test suite for GenAI specific attribute functions."""

    def test_genai_base_attributes_basic(self):
        """Test GenAI base attributes generation."""
        with patch.dict('os.environ', {}, clear=True):
            attrs = _genai_base_attributes(
                model_name="gpt-4",
                provider="openai",
                operation_name="chat"
            )
            
            assert attrs[ATTR_GENAI_REQUEST_MODEL] == "gpt-4"
            assert attrs[ATTR_GENAI_PROVIDER] == "openai"
            assert attrs[ATTR_GENAI_OPERATION_NAME] == "chat"
            assert attrs[ATTR_CAPABILITY] == str(Module.AICORE)
            assert attrs[ATTR_FUNCTIONALITY] == "model_call"

    def test_genai_base_attributes_includes_defaults(self):
        """Test that GenAI base attributes include default SDK attributes."""
        attrs = _genai_base_attributes(
            model_name="claude-3-opus",
            provider="anthropic",
            operation_name="chat"
        )
        
        # Should include default operation attributes
        assert ATTR_SOURCE in attrs
        assert ATTR_DEPRECATED in attrs


class TestRecordRequestMetric:
    """Test suite for record_request_metric function."""

    def test_record_request_metric_basic(self):
        """Test recording a basic request metric."""
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module
        
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
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module
        
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
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module
        
        # Reset counter to None to trigger initialization
        telemetry_module._request_counter = None
        
        with patch('cloud_sdk_python.core.telemetry.telemetry._initialize_metrics') as mock_init:
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
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module
        
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
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module
        
        telemetry_module._request_counter = None
        
        with patch('cloud_sdk_python.core.telemetry.telemetry._initialize_metrics'):
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
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module
        
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
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module
        
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
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module
        
        telemetry_module._error_counter = None
        
        with patch('cloud_sdk_python.core.telemetry.telemetry._initialize_metrics') as mock_init:
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
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module
        
        mock_counter = MagicMock()
        mock_counter.add.side_effect = Exception("Test error")
        telemetry_module._error_counter = mock_counter
        
        # Should not raise exception
        record_error_metric(
            module=Module.DESTINATION,
            source=None,
            operation="create_destination"
        )

class TestRecordAICoreMetric:
    """Test suite for updated record_aicore_metric function."""

    def test_record_aicore_metric_with_new_signature(self):
        """Test recording AI Core metric with new mandatory parameters."""
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module

        mock_histogram = MagicMock()
        telemetry_module._aicore_token_histogram = mock_histogram

        record_aicore_metric(
            model_name="gpt-4",
            provider="openai",
            operation_name="chat",
            input_tokens=100,
            output_tokens=50
        )

        # Should record twice - once for input, once for output
        assert mock_histogram.record.call_count == 2

        # Check first call (input tokens)
        first_call = mock_histogram.record.call_args_list[0]
        assert first_call[0][0] == 100
        input_attrs = first_call[0][1]
        assert input_attrs[ATTR_GENAI_REQUEST_MODEL] == "gpt-4"
        assert input_attrs[ATTR_GENAI_PROVIDER] == "openai"
        assert input_attrs[ATTR_GENAI_OPERATION_NAME] == "chat"
        assert input_attrs[ATTR_GENAI_TOKEN_TYPE] == "input"

        # Check second call (output tokens)
        second_call = mock_histogram.record.call_args_list[1]
        assert second_call[0][0] == 50
        output_attrs = second_call[0][1]
        assert output_attrs[ATTR_GENAI_TOKEN_TYPE] == "output"

    def test_record_aicore_metric_with_custom_attributes(self):
        """Test recording AI Core metric with custom attributes."""
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module

        mock_histogram = MagicMock()
        telemetry_module._aicore_token_histogram = mock_histogram

        custom_attrs = {
            "user_id": "user123",
            "session_id": "session456"
        }

        record_aicore_metric(
            model_name="gpt-4",
            provider="openai",
            operation_name="chat",
            input_tokens=100,
            output_tokens=50,
            custom_attributes=custom_attrs
        )

        # Check custom attributes are included
        first_call_attrs = mock_histogram.record.call_args_list[0][0][1]
        assert first_call_attrs["user_id"] == "user123"
        assert first_call_attrs["session_id"] == "session456"

    def test_initialize_aicore_metrics_creates_histogram(self):
        """Test that AI Core metrics creates a histogram not a counter."""
        import cloud_sdk_python.core.telemetry.telemetry as telemetry_module

        telemetry_module._aicore_token_histogram = None

        mock_meter = MagicMock()
        mock_histogram = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram

        with patch('cloud_sdk_python.core.telemetry.telemetry.get_meter', return_value=mock_meter):
            _initialize_aicore_metrics()

            assert telemetry_module._aicore_token_histogram is mock_histogram

            # Verify create_histogram was called
            mock_meter.create_histogram.assert_called_once()
            call_args = mock_meter.create_histogram.call_args
            assert call_args[1]['name'] == LLM_TOKEN_HISTOGRAM_NAME
            assert call_args[1]['unit'] == "{tokens}"
