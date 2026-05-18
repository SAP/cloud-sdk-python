"""Unit tests for cloud SDK data anonymization configuration."""

import base64
from dataclasses import is_dataclass
import importlib

from sap_cloud_sdk.core.data_anonymization.config import (
    DataAnonymizationConfig,
    _BindingData,
    _load_config_from_env,
)
from sap_cloud_sdk.core.data_anonymization.exceptions import ClientCreationError


secret_resolver = importlib.import_module("sap_cloud_sdk.core.secret_resolver")

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


class TestDataAnonymizationConfig:
    def test_valid_inline_config(self) -> None:
        config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            cert=CLIENT_CERT_BASE64,
            key=CLIENT_KEY_BASE64,
        )

        assert config.service_url == "https://service.example.com"
        assert config.cert == CLIENT_CERT_BASE64
        assert config.key == CLIENT_KEY_BASE64
        assert config.destination_name is None

    def test_valid_destination_config(self) -> None:
        config = DataAnonymizationConfig(
            service_url="https://service.example.com",
            destination_name="anon-destination",
        )

        assert config.destination_name == "anon-destination"

    def test_missing_service_url_raises(self) -> None:
        assert_raises(
            ValueError,
            "service_url is required",
            DataAnonymizationConfig,
            service_url="",
            cert=CLIENT_CERT_BASE64,
            key=CLIENT_KEY_BASE64,
        )

    def test_missing_keystore_raises(self) -> None:
        assert_raises(
            ValueError,
            "A Key Store is required",
            DataAnonymizationConfig,
            service_url="https://service.example.com",
        )

    def test_partial_inline_keystore_raises(self) -> None:
        assert_raises(
            ValueError,
            "cert and key must both be set together",
            DataAnonymizationConfig,
            service_url="https://service.example.com",
            cert=CLIENT_CERT_BASE64,
        )

    def test_is_dataclass(self) -> None:
        assert is_dataclass(DataAnonymizationConfig)


class TestBindingData:
    def test_validate_success_with_inline_values(self) -> None:
        binding = _BindingData(
            url="https://service.example.com",
            cert=CLIENT_CERT_BASE64,
            key=CLIENT_KEY_BASE64,
        )

        binding.validate()

    def test_validate_success_with_destination(self) -> None:
        binding = _BindingData(
            url="https://service.example.com",
            destination_name="anon-destination",
        )

        binding.validate()

    def test_validate_missing_url_raises(self) -> None:
        binding = _BindingData(url="", destination_name="anon-destination")

        assert_raises(ValueError, "url is required", binding.validate)

    def test_validate_missing_keystore_data_raises(self) -> None:
        binding = _BindingData(url="https://service.example.com")

        assert_raises(ValueError, "Binding must contain", binding.validate)

    def test_extract_config(self) -> None:
        binding = _BindingData(
            url="https://service.example.com",
            cert=CLIENT_CERT_BASE64,
            key=CLIENT_KEY_BASE64,
        )

        config = binding.extract_config()

        assert isinstance(config, DataAnonymizationConfig)
        assert config.service_url == "https://service.example.com"


class TestLoadConfigFromEnv:
    def test_load_config_success(self, monkeypatch) -> None:
        def fake_read(mount_path, env_var, service, instance, binding_data):
            assert mount_path == "/etc/secrets/appfnd"
            assert env_var == "CLOUD_SDK_CFG"
            assert service == "data-anonymization"
            assert instance == "custom-instance"
            binding_data.url = "https://service.example.com"
            binding_data.destination_name = "anon-destination"

        monkeypatch.setattr(
            secret_resolver,
            "read_from_mount_and_fallback_to_env_var",
            fake_read,
        )

        config = _load_config_from_env("custom-instance")

        assert config.service_url == "https://service.example.com"
        assert config.destination_name == "anon-destination"

    def test_load_config_failure_wraps_exception(
        self,
        monkeypatch,
    ) -> None:
        def fake_read(*args, **kwargs):
            raise RuntimeError("read failed")

        monkeypatch.setattr(
            secret_resolver,
            "read_from_mount_and_fallback_to_env_var",
            fake_read,
        )

        assert_raises(
            ClientCreationError,
            "Failed to load configuration",
            _load_config_from_env,
        )
