"""Tests for telemetry configuration."""

from unittest.mock import patch

from sap_cloud_sdk.core.telemetry.config import (
    InstrumentationConfig,
    create_resource_attributes_from_env,
    get_config,
    set_config,
)
from sap_cloud_sdk.core.telemetry.constants import (
    ATTR_MLFLOW_EXPERIMENT_ID,
    ATTR_SAP_SOLUTION_AREA,
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
        import sap_cloud_sdk.core.telemetry.config as config_module
        config_module._config = None

        with patch.dict('os.environ', {}, clear=True):
            config1 = get_config()
            config2 = get_config()

            assert config1 is config2

    def test_get_config_initializes_from_env(self):
        """Test that get_config initializes from environment."""
        # Reset global config
        import sap_cloud_sdk.core.telemetry.config as config_module
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
        import sap_cloud_sdk.core.telemetry.config as config_module
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
        import sap_cloud_sdk.core.telemetry.config as config_module
        config_module._config = None

        config1 = InstrumentationConfig(enabled=True, otlp_endpoint="http://endpoint1:4317")
        set_config(config1)

        assert get_config() is config1

        config2 = InstrumentationConfig(enabled=False, otlp_endpoint="http://endpoint2:4317")
        set_config(config2)

        assert get_config() is config2
        assert get_config() is not config1


class TestCreateResourceAttributesFromEnv:
    """Test suite for create_resource_attributes_from_env."""

    def test_solution_area_defaults_to_unknown(self):
        """sap.solution_area defaults to 'unknown' when env var is unset."""
        with patch.dict('os.environ', {}, clear=True):
            attrs = create_resource_attributes_from_env()

            assert attrs[ATTR_SAP_SOLUTION_AREA] == "unknown"

    def test_mlflow_experiment_id_omitted_when_unset(self):
        """mlflow.experiment_id is omitted entirely when env var is unset.

        We deliberately do not emit a placeholder value because that would
        pollute MLflow and mislead downstream routing logic.
        """
        with patch.dict('os.environ', {}, clear=True):
            attrs = create_resource_attributes_from_env()

            assert ATTR_MLFLOW_EXPERIMENT_ID not in attrs

    def test_mlflow_experiment_id_omitted_when_empty(self):
        """mlflow.experiment_id is omitted when env var is an empty string."""
        with patch.dict('os.environ', {'MLFLOW_EXPERIMENT_ID': ''}, clear=True):
            attrs = create_resource_attributes_from_env()

            assert ATTR_MLFLOW_EXPERIMENT_ID not in attrs

    def test_solution_area_read_from_env(self):
        """sap.solution_area resource attribute is read from SAP_SOLUTION_AREA."""
        with patch.dict('os.environ', {'SAP_SOLUTION_AREA': 'HCM'}, clear=True):
            attrs = create_resource_attributes_from_env()

            assert attrs[ATTR_SAP_SOLUTION_AREA] == "HCM"

    def test_mlflow_experiment_id_read_from_env(self):
        """mlflow.experiment_id resource attribute is read from MLFLOW_EXPERIMENT_ID."""
        with patch.dict('os.environ', {'MLFLOW_EXPERIMENT_ID': '42'}, clear=True):
            attrs = create_resource_attributes_from_env()

            assert attrs[ATTR_MLFLOW_EXPERIMENT_ID] == "42"

    def test_both_new_attributes_read_together(self):
        """Both new attributes are populated independently from their env vars."""
        with patch.dict('os.environ', {
            'SAP_SOLUTION_AREA': 'FIN',
            'MLFLOW_EXPERIMENT_ID': 'exp-123',
        }, clear=True):
            attrs = create_resource_attributes_from_env()

            assert attrs[ATTR_SAP_SOLUTION_AREA] == "FIN"
            assert attrs[ATTR_MLFLOW_EXPERIMENT_ID] == "exp-123"

    def test_solution_area_key_always_present(self):
        """sap.solution_area is always emitted (defaults to 'unknown')."""
        with patch.dict('os.environ', {}, clear=True):
            attrs = create_resource_attributes_from_env()

            assert "sap.solution_area" in attrs
