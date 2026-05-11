"""Unit tests for AgentMemoryConfig, BindingData, and _load_config_from_env."""

from unittest.mock import patch

import pytest

from sap_cloud_sdk.agent_memory.config import (
    AgentMemoryConfig,
    BindingData,
    _load_config_from_env,
)
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryConfigError


# ── AgentMemoryConfig ─────────────────────────────────────────────────────────


class TestAgentMemoryConfig:
    def test_raises_when_base_url_empty(self):
        """AgentMemoryConfig rejects an empty base_url."""
        with pytest.raises(AgentMemoryConfigError, match="base_url"):
            AgentMemoryConfig(base_url="")

    def test_optional_fields_default_to_none(self):
        """token_url, client_id, and client_secret default to None."""
        config = AgentMemoryConfig(base_url="http://localhost:8080")
        assert config.token_url is None
        assert config.client_id is None
        assert config.client_secret is None

    def test_timeout_default(self):
        """Default timeout is 30.0 seconds."""
        config = AgentMemoryConfig(base_url="http://localhost:8080")
        assert config.timeout == 30.0


# ── BindingData ───────────────────────────────────────────────────────────────


class TestBindingData:
    def test_validate_raises_when_all_fields_empty(self):
        """validate() raises AgentMemoryConfigError when all fields are empty."""
        with pytest.raises(AgentMemoryConfigError, match="missing required fields"):
            BindingData().validate()

    def test_validate_raises_when_some_fields_empty(self):
        """validate() raises when only some fields are populated."""
        binding = BindingData(application_url="https://example.com")
        with pytest.raises(AgentMemoryConfigError, match="missing required fields"):
            binding.validate()

    def test_validate_passes_when_all_fields_set(self):
        """validate() does not raise when all required fields are populated."""
        binding = BindingData(
            application_url="https://example.com",
            uaa_url="https://auth.example.com",
            uaa_clientid="client-id",
            uaa_clientsecret="client-secret",
        )
        binding.validate()  # should not raise

    def test_extract_config_derives_token_url(self):
        """extract_config() appends /oauth/token to uaa_url."""
        binding = BindingData(
            application_url="https://memory.example.com",
            uaa_url="https://auth.example.com",
            uaa_clientid="cid",
            uaa_clientsecret="csec",
        )
        config = binding.extract_config()
        assert config.token_url == "https://auth.example.com/oauth/token"

    def test_extract_config_strips_trailing_slash_from_uaa_url(self):
        """extract_config() strips a trailing slash before appending /oauth/token."""
        binding = BindingData(
            application_url="https://memory.example.com",
            uaa_url="https://auth.example.com/",
            uaa_clientid="cid",
            uaa_clientsecret="csec",
        )
        config = binding.extract_config()
        assert config.token_url == "https://auth.example.com/oauth/token"

    def test_extract_config_maps_all_fields(self):
        """extract_config() maps all binding fields to AgentMemoryConfig."""
        binding = BindingData(
            application_url="https://memory.example.com",
            uaa_url="https://auth.example.com",
            uaa_clientid="my-client",
            uaa_clientsecret="my-secret",
        )
        config = binding.extract_config()
        assert config.base_url == "https://memory.example.com"
        assert config.client_id == "my-client"
        assert config.client_secret == "my-secret"


# ── _load_config_from_env ─────────────────────────────────────────────────────

_MOUNT_LOADER = "sap_cloud_sdk.core.secret_resolver.resolver._load_from_mount"

_ENV_VARS = {
    "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL": "https://memory.example.com",
    "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA_URL": "https://auth.example.com",
    "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA_CLIENTID": "env-client",
    "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA_CLIENTSECRET": "env-secret",
}


def _fill_binding(_base_volume_mount, _module, _instance, target) -> None:
    target.application_url = "https://memory.example.com"
    target.uaa_url = "https://auth.example.com"
    target.uaa_clientid = "resolved-client"
    target.uaa_clientsecret = "resolved-secret"


class TestLoadConfigFromEnv:
    def test_success_from_mount(self):
        """_load_config_from_env() returns a valid AgentMemoryConfig when mount succeeds."""
        with patch(_MOUNT_LOADER, side_effect=_fill_binding):
            config = _load_config_from_env()

        assert config.base_url == "https://memory.example.com"
        assert config.token_url == "https://auth.example.com/oauth/token"
        assert config.client_id == "resolved-client"
        assert config.client_secret == "resolved-secret"

    def test_calls_mount_loader_with_correct_arguments(self):
        """_load_config_from_env() calls _load_from_mount with the correct path/module/instance."""
        with patch(_MOUNT_LOADER, side_effect=_fill_binding) as mock_mount:
            _load_config_from_env()

        mock_mount.assert_called_once()
        args = mock_mount.call_args[0]
        assert args[0] == "/etc/secrets/appfnd"
        assert args[1] == "hana-agent-memory"
        assert args[2] == "default"

    def test_falls_back_to_env_when_mount_fails(self, monkeypatch):
        """_load_config_from_env() reads env vars when the mount path is unavailable."""
        for var, val in _ENV_VARS.items():
            monkeypatch.setenv(var, val)

        with patch(_MOUNT_LOADER, side_effect=FileNotFoundError("no mount")):
            config = _load_config_from_env()

        assert config.base_url == "https://memory.example.com"
        assert config.client_id == "env-client"

    def test_raises_config_error_when_mount_and_env_both_fail(self, monkeypatch):
        """_load_config_from_env() raises AgentMemoryConfigError when both mount and env vars are absent."""
        for var in _ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with patch(_MOUNT_LOADER, side_effect=FileNotFoundError("no mount")):
            with pytest.raises(
                AgentMemoryConfigError, match="Missing required environment variables"
            ):
                _load_config_from_env()

    def test_raises_config_error_when_mount_binding_incomplete_and_env_missing(
        self, monkeypatch
    ):
        """_load_config_from_env() raises AgentMemoryConfigError when mount gives partial data and env is absent."""
        for var in _ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        def incomplete_fill(_bvm, _mod, _inst, target):
            target.application_url = "https://example.com"
            # uaa_url/uaa_clientid/uaa_clientsecret remain empty → validate() raises

        with patch(_MOUNT_LOADER, side_effect=incomplete_fill):
            with pytest.raises(AgentMemoryConfigError):
                _load_config_from_env()
