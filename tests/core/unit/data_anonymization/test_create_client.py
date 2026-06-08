"""Unit tests for the client factory."""

import base64
from unittest.mock import patch

import sap_cloud_sdk.core.data_anonymization as data_anonymization
from sap_cloud_sdk.core.data_anonymization import create_client
from sap_cloud_sdk.core.data_anonymization.client import DataAnonymizationClient
from sap_cloud_sdk.core.data_anonymization.config import DataAnonymizationConfig
from sap_cloud_sdk.core.data_anonymization.exceptions import ClientCreationError
from sap_cloud_sdk.core.telemetry import Module, Operation


CLIENT_CERT_BASE64 = base64.b64encode(
    b"-----BEGIN CERTIFICATE-----\nCERT\n-----END CERTIFICATE-----\n"
).decode("utf-8")
CLIENT_KEY_BASE64 = base64.b64encode(
    b"-----BEGIN RSA PRIVATE KEY-----\nKEY\n-----END RSA PRIVATE KEY-----\n"
).decode("utf-8")


def assert_raises(exception_type, match, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exception_type as error:
        assert match in str(error)
        return error
    raise AssertionError(f"Expected {exception_type.__name__} to be raised")


class DummyTransport:
    def close(self) -> None:
        pass


class TestCreateClient:
    def test_create_client_uses_loaded_config(
        self,
        monkeypatch,
    ) -> None:
        config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            destination_name="anon-destination",
        )
        transport = DummyTransport()

        monkeypatch.setattr(
            data_anonymization,
            "_load_config_from_env",
            lambda instance: config,
        )
        monkeypatch.setattr(data_anonymization, "HttpTransport", lambda resolved: transport)

        client = create_client(instance="custom")

        assert isinstance(client, DataAnonymizationClient)
        assert client._transport is transport

    def test_create_client_uses_explicit_config(
        self,
        monkeypatch,
    ) -> None:
        config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            cert=CLIENT_CERT_BASE64,
            key=CLIENT_KEY_BASE64,
        )
        transport = DummyTransport()

        monkeypatch.setattr(data_anonymization, "HttpTransport", lambda resolved: transport)

        client = create_client(config=config)

        assert isinstance(client, DataAnonymizationClient)
        assert client._transport is transport

    def test_create_client_wraps_errors(self, monkeypatch) -> None:
        def fail(instance: str):
            raise RuntimeError("boom")

        monkeypatch.setattr(data_anonymization, "_load_config_from_env", fail)

        assert_raises(
            ClientCreationError,
            "Failed to create DataAnonymizationClient",
            create_client,
        )

    def test_create_client_records_request_metric_without_sensitive_config(
        self,
        monkeypatch,
    ) -> None:
        config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            cert=CLIENT_CERT_BASE64,
            key=CLIENT_KEY_BASE64,
        )
        transport = DummyTransport()

        monkeypatch.setattr(data_anonymization, "HttpTransport", lambda resolved: transport)

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_request_metric"
        ) as mock_metric:
            client = create_client(config=config)

        assert isinstance(client, DataAnonymizationClient)
        mock_metric.assert_called_once_with(
            Module.DATA_ANONYMIZATION,
            None,
            Operation.DATA_ANONYMIZATION_CREATE_CLIENT,
            False,
        )
        assert CLIENT_CERT_BASE64 not in str(mock_metric.call_args)
        assert CLIENT_KEY_BASE64 not in str(mock_metric.call_args)

    def test_create_client_records_error_metric_on_failure(self, monkeypatch) -> None:
        def fail(instance: str):
            raise RuntimeError("boom")

        monkeypatch.setattr(data_anonymization, "_load_config_from_env", fail)

        with patch(
            "sap_cloud_sdk.core.telemetry.metrics_decorator.record_error_metric"
        ) as mock_metric:
            assert_raises(
                ClientCreationError,
                "Failed to create DataAnonymizationClient",
                create_client,
            )

        mock_metric.assert_called_once_with(
            Module.DATA_ANONYMIZATION,
            None,
            Operation.DATA_ANONYMIZATION_CREATE_CLIENT,
            False,
        )
