"""Tests for telemetry configuration."""

import pytest
from unittest.mock import patch

from cloud_sdk_python.core.telemetry.config import (
    InstrumentationConfig,
    get_config,
    set_config,
    _config
)


class TestInstrumentationConfig:
    """Test suite for InstrumentationConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = InstrumentationConfig()
        
        assert config.enabled is False
        assert config.service_name == "application-foundation-sdk"
        assert config.otlp_endpoint == ""

    def test_from_env_disabled_by_default(self):
        """Test that telemetry is disabled when no endpoint is configured."""
        with patch.dict('os.environ', {}, clear=True):
            config = InstrumentationConfig.from_env()
            
            assert config.enabled is False
            assert config.otlp_endpoint == ""
            assert config.service_name == "unknown"

    def test_from_env_enabled_with_endpoint(self):
        """Test that telemetry is enabled when endpoint is configured."""
        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'
        }, clear=True):
            config = InstrumentationConfig.from_env()
            
            assert config.enabled is True
            assert config.otlp_endpoint == 'http://localhost:4317'
            assert config.service_name == "unknown"

    def test_from_env_explicit_disable(self):
        """Test explicit disable with CLOUD_SDK_OTEL_DISABLED=true."""
        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317',
            'CLOUD_SDK_OTEL_DISABLED': 'true'
        }, clear=True):
            config = InstrumentationConfig.from_env()
            
            assert config.enabled is False
            assert config.otlp_endpoint == 'http://localhost:4317'

    def test_from_env_explicit_disable_case_insensitive(self):
        """Test explicit disable is case insensitive."""
        test_cases = ['true', 'True', 'TRUE', 'TrUe']
        
        for disable_value in test_cases:
            with patch.dict('os.environ', {
                'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317',
                'CLOUD_SDK_OTEL_DISABLED': disable_value
            }, clear=True):
                config = InstrumentationConfig.from_env()
                
                assert config.enabled is False, f"Failed for CLOUD_SDK_OTEL_DISABLED={disable_value}"

    def test_from_env_not_disabled_with_false(self):
        """Test that CLOUD_SDK_OTEL_DISABLED=false does not disable."""
        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317',
            'CLOUD_SDK_OTEL_DISABLED': 'false'
        }, clear=True):
            config = InstrumentationConfig.from_env()
            
            assert config.enabled is True

    def test_from_env_not_disabled_with_invalid_value(self):
        """Test that invalid CLOUD_SDK_OTEL_DISABLED values don't disable."""
        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317',
            'CLOUD_SDK_OTEL_DISABLED': 'yes'
        }, clear=True):
            config = InstrumentationConfig.from_env()
            
            assert config.enabled is True

    def test_from_env_empty_endpoint_disables(self):
        """Test that empty endpoint string disables telemetry."""
        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': ''
        }, clear=True):
            config = InstrumentationConfig.from_env()
            
            assert config.enabled is False

    def test_service_name_is_fixed(self):
        """Test that service name defaults to unknown when APPFND_CONHOS_APP_NAME is not set."""
        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://localhost:4317'
        }, clear=True):
            config = InstrumentationConfig.from_env()
            
            assert config.service_name == "unknown"


class TestGlobalConfig:
    """Test suite for global configuration functions."""

    def test_get_config_returns_singleton(self):
        """Test that get_config returns the same instance."""
        # Reset global config
        import cloud_sdk_python.core.telemetry.config as config_module
        config_module._config = None
        
        with patch.dict('os.environ', {}, clear=True):
            config1 = get_config()
            config2 = get_config()
            
            assert config1 is config2

    def test_get_config_initializes_from_env(self):
        """Test that get_config initializes from environment."""
        # Reset global config
        import cloud_sdk_python.core.telemetry.config as config_module
        config_module._config = None
        
        with patch.dict('os.environ', {
            'OTEL_EXPORTER_OTLP_ENDPOINT': 'http://test:4317'
        }, clear=True):
            config = get_config()
            
            assert config.enabled is True
            assert config.otlp_endpoint == 'http://test:4317'

    def test_set_config_overrides_global(self):
        """Test that set_config overrides the global configuration."""
        # Reset global config
        import cloud_sdk_python.core.telemetry.config as config_module
        config_module._config = None
        
        custom_config = InstrumentationConfig(
            enabled=True,
            service_name="custom-service",
            otlp_endpoint="http://custom:4317"
        )
        
        set_config(custom_config)
        retrieved_config = get_config()
        
        assert retrieved_config is custom_config
        assert retrieved_config.service_name == "custom-service"
        assert retrieved_config.otlp_endpoint == "http://custom:4317"

    def test_set_config_affects_subsequent_get_config(self):
        """Test that set_config affects all subsequent get_config calls."""
        # Reset global config
        import cloud_sdk_python.core.telemetry.config as config_module
        config_module._config = None
        
        config1 = InstrumentationConfig(enabled=True, otlp_endpoint="http://endpoint1:4317")
        set_config(config1)
        
        assert get_config() is config1
        
        config2 = InstrumentationConfig(enabled=False, otlp_endpoint="http://endpoint2:4317")
        set_config(config2)
        
        assert get_config() is config2
        assert get_config() is not config1