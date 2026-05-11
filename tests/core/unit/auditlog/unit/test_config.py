"""Tests for configuration parsing."""

import json
import pytest
from unittest.mock import patch, MagicMock

from sap_cloud_sdk.core.auditlog.config import (
    AuditLogConfig,
    BindingData,
    _load_config_from_env
)
from sap_cloud_sdk.core.auditlog.exceptions import ClientCreationError


class TestAuditLogConfig:

    def test_valid_initialization(self):
        config = AuditLogConfig(
            client_id="test_client",
            client_secret="test_secret",
            oauth_url="https://oauth.example.com",
            service_url="https://service.example.com"
        )
        assert config.client_id == "test_client"
        assert config.client_secret == "test_secret"
        assert config.oauth_url == "https://oauth.example.com"
        assert config.service_url == "https://service.example.com"

    def test_empty_client_id(self):
        with pytest.raises(ValueError, match="client_id is required"):
            AuditLogConfig(
                client_id="",
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

    def test_none_client_id(self):
        with pytest.raises(ValueError, match="client_id is required"):
            AuditLogConfig(
                client_id=None,  # ty: ignore[invalid-argument-type]
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

    def test_empty_client_secret(self):
        with pytest.raises(ValueError, match="client_secret is required"):
            AuditLogConfig(
                client_id="test_client",
                client_secret="",
                oauth_url="https://oauth.example.com",
                service_url="https://service.example.com"
            )

    def test_empty_oauth_url(self):
        with pytest.raises(ValueError, match="oauth_url is required"):
            AuditLogConfig(
                client_id="test_client",
                client_secret="test_secret",
                oauth_url="",
                service_url="https://service.example.com"
            )

    def test_empty_service_url(self):
        with pytest.raises(ValueError, match="service_url is required"):
            AuditLogConfig(
                client_id="test_client",
                client_secret="test_secret",
                oauth_url="https://oauth.example.com",
                service_url=""
            )

    def test_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(AuditLogConfig)


class TestBindingData:

    def test_initialization(self):
        binding = BindingData(
            url="https://service.example.com",
            uaa='{"clientid": "test", "clientsecret": "secret", "url": "oauth"}'
        )
        assert binding.url == "https://service.example.com"
        assert "clientid" in binding.uaa

    def test_validate_success(self):
        binding = BindingData(
            url="https://service.example.com",
            uaa='{"clientid": "test"}'
        )
        binding.validate()

    def test_validate_empty_url(self):
        binding = BindingData(url="", uaa='{"clientid": "test"}')
        with pytest.raises(ValueError, match="url is required"):
            binding.validate()

    def test_validate_empty_uaa(self):
        binding = BindingData(url="https://service.example.com", uaa="")
        with pytest.raises(ValueError, match="uaa field is required"):
            binding.validate()

    def test_extract_config_success(self):
        uaa_json = {
            "clientid": "test_client",
            "clientsecret": "test_secret",
            "url": "https://oauth.example.com"
        }
        binding = BindingData(
            url="https://service.example.com",
            uaa=json.dumps(uaa_json)
        )

        config = binding.extract_config()

        assert config.client_id == "test_client"
        assert config.client_secret == "test_secret"
        assert config.oauth_url == "https://oauth.example.com"
        assert config.service_url == "https://service.example.com"

    def test_extract_config_empty_uaa(self):
        binding = BindingData(url="https://service.example.com", uaa="")
        with pytest.raises(ClientCreationError, match="UAA field is empty"):
            binding.extract_config()

    def test_extract_config_invalid_json(self):
        binding = BindingData(
            url="https://service.example.com",
            uaa="invalid json"
        )
        with pytest.raises(ClientCreationError, match="Failed to parse UAA JSON"):
            binding.extract_config()

    def test_extract_config_missing_clientid(self):
        uaa_json = {
            "clientsecret": "test_secret",
            "url": "https://oauth.example.com"
        }
        binding = BindingData(
            url="https://service.example.com",
            uaa=json.dumps(uaa_json)
        )
        with pytest.raises(ClientCreationError, match="Missing required field in UAA JSON"):
            binding.extract_config()

    def test_extract_config_missing_clientsecret(self):
        uaa_json = {
            "clientid": "test_client",
            "url": "https://oauth.example.com"
        }
        binding = BindingData(
            url="https://service.example.com",
            uaa=json.dumps(uaa_json)
        )
        with pytest.raises(ClientCreationError, match="Missing required field in UAA JSON"):
            binding.extract_config()

    def test_extract_config_missing_url(self):
        uaa_json = {
            "clientid": "test_client",
            "clientsecret": "test_secret"
        }
        binding = BindingData(
            url="https://service.example.com",
            uaa=json.dumps(uaa_json)
        )
        with pytest.raises(ClientCreationError, match="Missing required field in UAA JSON"):
            binding.extract_config()

    def test_extract_config_with_strict_false(self):
        uaa_json_with_comments = '''
        {
            "clientid": "test_client",
            "clientsecret": "test_secret",
            "url": "https://oauth.example.com"
            // This would normally break strict JSON parsing
        }
        '''
        binding = BindingData(
            url="https://service.example.com",
            uaa=uaa_json_with_comments.replace("//", "").replace("This would normally break strict JSON parsing", "")
        )

        config = binding.extract_config()
        assert config.client_id == "test_client"

    def test_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(BindingData)


class TestLoadConfigFromEnv:

    @patch('sap_cloud_sdk.core.secret_resolver.read_from_mount_and_fallback_to_env_var')
    def test_load_config_success(self, mock_read):
        mock_binding = BindingData(
            url="https://service.example.com",
            uaa='{"clientid": "test", "clientsecret": "secret", "url": "oauth"}'
        )

        def mock_read_side_effect(*args, **kwargs):
            binding_data: BindingData = kwargs["target"]
            binding_data.url = mock_binding.url
            binding_data.uaa = mock_binding.uaa

        mock_read.side_effect = mock_read_side_effect

        config = _load_config_from_env()

        assert config.client_id == "test"
        assert config.client_secret == "secret"
        assert config.oauth_url == "oauth"
        assert config.service_url == "https://service.example.com"

        mock_read.assert_called_once_with(
            base_volume_mount="/etc/secrets/appfnd",
            base_var_name="CLOUD_SDK_CFG",
            module="auditlog",
            instance="default",
            target=mock_read.call_args.kwargs["target"]
        )

    @patch('sap_cloud_sdk.core.secret_resolver.read_from_mount_and_fallback_to_env_var')
    def test_load_config_validation_error(self, mock_read):
        def mock_read_side_effect(*args, **kwargs):
            binding_data: BindingData = kwargs["target"]
            binding_data.url = ""
            binding_data.uaa = ""

        mock_read.side_effect = mock_read_side_effect

        with pytest.raises(ClientCreationError, match="Failed to load configuration"):
            _load_config_from_env()

    @patch('sap_cloud_sdk.core.secret_resolver.read_from_mount_and_fallback_to_env_var')
    def test_load_config_read_exception(self, mock_read):
        mock_read.side_effect = Exception("Mount read failed")

        with pytest.raises(ClientCreationError, match="Failed to load configuration"):
            _load_config_from_env()

    @patch('sap_cloud_sdk.core.secret_resolver.read_from_mount_and_fallback_to_env_var')
    def test_load_config_invalid_uaa(self, mock_read):
        def mock_read_side_effect(*args, **kwargs):
            binding_data: BindingData = kwargs["target"]
            binding_data.url = "https://service.example.com"
            binding_data.uaa = "invalid json"

        mock_read.side_effect = mock_read_side_effect

        with pytest.raises(ClientCreationError, match="Failed to load configuration"):
            _load_config_from_env()
