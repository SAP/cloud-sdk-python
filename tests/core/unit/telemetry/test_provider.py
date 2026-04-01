"""Tests for telemetry meter provider."""

import pytest
from unittest.mock import patch, MagicMock

from opentelemetry.sdk.metrics import Counter, Histogram, ObservableCounter, ObservableGauge, ObservableUpDownCounter, UpDownCounter
from opentelemetry.sdk.metrics.export import AggregationTemporality

from sap_cloud_sdk.core.telemetry._provider import (
    get_meter,
    shutdown,
    _setup_meter_provider,
)
from sap_cloud_sdk.core.telemetry.config import InstrumentationConfig


class TestGetMeter:
    """Test suite for get_meter function."""

    def test_get_meter_returns_meter(self):
        """Test that get_meter returns a meter instance."""
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        # Reset global state
        provider_module._meter_provider = None
        provider_module._meter = None

        with patch('sap_cloud_sdk.core.telemetry._provider._setup_meter_provider') as mock_setup:
            mock_provider = MagicMock()
            mock_setup.return_value = mock_provider

            with patch('opentelemetry.metrics.get_meter') as mock_get_meter:
                mock_meter = MagicMock()
                mock_get_meter.return_value = mock_meter

                meter = get_meter()

                assert meter is mock_meter
                mock_setup.assert_called_once()

    def test_get_meter_returns_singleton(self):
        """Test that get_meter returns the same meter instance."""
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        # Reset global state
        provider_module._meter_provider = None
        provider_module._meter = None

        with patch('sap_cloud_sdk.core.telemetry._provider._setup_meter_provider') as mock_setup:
            mock_provider = MagicMock()
            mock_setup.return_value = mock_provider

            with patch('opentelemetry.metrics.get_meter') as mock_get_meter:
                mock_meter = MagicMock()
                mock_get_meter.return_value = mock_meter

                meter1 = get_meter()
                meter2 = get_meter()

                assert meter1 is meter2
                # Setup should only be called once
                mock_setup.assert_called_once()

    def test_get_meter_when_provider_setup_fails(self):
        """Test that get_meter returns no-op meter when provider setup fails."""
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        # Reset global state
        provider_module._meter_provider = None
        provider_module._meter = None

        with patch('sap_cloud_sdk.core.telemetry._provider._setup_meter_provider', return_value=None):
            with patch('opentelemetry.metrics.get_meter_provider') as mock_get_provider:
                mock_no_op_provider = MagicMock()
                mock_no_op_meter = MagicMock()
                mock_no_op_provider.get_meter.return_value = mock_no_op_meter
                mock_get_provider.return_value = mock_no_op_provider

                meter = get_meter()

                assert meter is mock_no_op_meter
                mock_no_op_provider.get_meter.assert_called_once()

    def test_get_meter_initializes_provider_once(self):
        """Test that provider is only initialized once across multiple get_meter calls."""
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        # Reset global state
        provider_module._meter_provider = None
        provider_module._meter = None

        with patch('sap_cloud_sdk.core.telemetry._provider._setup_meter_provider') as mock_setup:
            mock_provider = MagicMock()
            mock_setup.return_value = mock_provider

            with patch('opentelemetry.metrics.get_meter') as mock_get_meter:
                mock_meter = MagicMock()
                mock_get_meter.return_value = mock_meter

                # Call get_meter multiple times
                get_meter()
                get_meter()
                get_meter()

                # Setup should only be called once
                assert mock_setup.call_count == 1


class TestShutdown:
    """Test suite for shutdown function."""

    def test_shutdown_with_active_provider(self):
        """Test shutdown with an active meter provider."""
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        mock_provider = MagicMock()
        provider_module._meter_provider = mock_provider

        shutdown()

        mock_provider.shutdown.assert_called_once()
        assert provider_module._meter_provider is None

    def test_shutdown_with_no_provider(self):
        """Test shutdown when no provider is active."""
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        provider_module._meter_provider = None

        # Should not raise exception
        shutdown()

    def test_shutdown_handles_exception(self):
        """Test that shutdown handles exceptions gracefully."""
        import sap_cloud_sdk.core.telemetry._provider as provider_module

        mock_provider = MagicMock()
        mock_provider.shutdown.side_effect = Exception("Shutdown error")
        provider_module._meter_provider = mock_provider

        # Should not raise exception
        shutdown()

        # Provider should still be set to None
        assert provider_module._meter_provider is None


class TestSetupMeterProvider:
    """Test suite for _setup_meter_provider function."""

    def test_setup_meter_provider_disabled(self):
        """Test that setup returns None when telemetry is disabled."""
        config = InstrumentationConfig(enabled=False)

        with patch('sap_cloud_sdk.core.telemetry._provider.get_config', return_value=config):
            provider = _setup_meter_provider()

            assert provider is None

    def test_setup_meter_provider_success(self):
        """Test successful meter provider setup."""
        config = InstrumentationConfig(
            enabled=True,
            service_name="test-service",
            otlp_endpoint="http://localhost:4317"
        )

        with patch('sap_cloud_sdk.core.telemetry._provider.get_config', return_value=config):
            with patch('sap_cloud_sdk.core.telemetry._provider.Resource') as mock_resource_class:
                with patch('sap_cloud_sdk.core.telemetry._provider.OTLPMetricExporter') as mock_exporter_class:
                    with patch('sap_cloud_sdk.core.telemetry._provider.PeriodicExportingMetricReader') as mock_reader_class:
                        with patch('sap_cloud_sdk.core.telemetry._provider.MeterProvider') as mock_provider_class:
                            with patch('opentelemetry.metrics.set_meter_provider') as mock_set_provider:
                                mock_resource = MagicMock()
                                mock_exporter = MagicMock()
                                mock_reader = MagicMock()
                                mock_provider = MagicMock()

                                mock_resource_class.return_value = mock_resource
                                mock_exporter_class.return_value = mock_exporter
                                mock_reader_class.return_value = mock_reader
                                mock_provider_class.return_value = mock_provider

                                result = _setup_meter_provider()

                                assert result is mock_provider

                                # Verify exporter was created with endpoint and delta temporality
                                mock_exporter_class.assert_called_once_with(
                                    endpoint="http://localhost:4317",
                                    preferred_temporality={
                                        Counter: AggregationTemporality.DELTA,
                                        Histogram: AggregationTemporality.DELTA,
                                        ObservableCounter: AggregationTemporality.DELTA,
                                        ObservableGauge: AggregationTemporality.DELTA,
                                        ObservableUpDownCounter: AggregationTemporality.DELTA,
                                        UpDownCounter: AggregationTemporality.DELTA,
                                    },
                                )

                                # Verify reader was created with exporter
                                mock_reader_class.assert_called_once_with(
                                    exporter=mock_exporter
                                )


                                # Verify provider was set globally
                                mock_set_provider.assert_called_once_with(mock_provider)

    def test_setup_meter_provider_with_valid_config(self):
        """Test setup with various valid configurations."""
        test_configs = [
            InstrumentationConfig(
                enabled=True,
                service_name="app1",
                otlp_endpoint="http://collector1:4317"
            ),
            InstrumentationConfig(
                enabled=True,
                service_name="app2",
                otlp_endpoint="https://collector2:4318"
            ),
        ]

        for config in test_configs:
            with patch('sap_cloud_sdk.core.telemetry._provider.get_config', return_value=config):
                with patch('sap_cloud_sdk.core.telemetry._provider.Resource'):
                    with patch('sap_cloud_sdk.core.telemetry._provider.OTLPMetricExporter') as mock_exporter:
                        with patch('sap_cloud_sdk.core.telemetry._provider.PeriodicExportingMetricReader'):
                            with patch('sap_cloud_sdk.core.telemetry._provider.MeterProvider') as mock_provider_class:
                                with patch('opentelemetry.metrics.set_meter_provider'):
                                    mock_provider = MagicMock()
                                    mock_provider_class.return_value = mock_provider

                                    result = _setup_meter_provider()

                                    assert result is mock_provider
                                    # Verify exporter was created with correct endpoint and delta temporality
                                    mock_exporter.assert_called_with(
                                        endpoint=config.otlp_endpoint,
                                        preferred_temporality={
                                            Counter: AggregationTemporality.DELTA,
                                            Histogram: AggregationTemporality.DELTA,
                                            ObservableCounter: AggregationTemporality.DELTA,
                                            ObservableGauge: AggregationTemporality.DELTA,
                                            ObservableUpDownCounter: AggregationTemporality.DELTA,
                                            UpDownCounter: AggregationTemporality.DELTA,
                                        },
                                    )
