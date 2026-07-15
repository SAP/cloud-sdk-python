"""Unit tests for AgentMemoryConfig, BindingData, and _load_config_from_env."""

import json
from unittest.mock import patch

import pytest

from sap_cloud_sdk.agent_memory.config import (
    AgentMemoryConfig,
    BindingData,
    _load_secrets,
)
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryConfigError

_VALID_UAA = json.dumps({
    "url": "https://auth.example.com",
    "clientid": "my-client",
    "clientsecret": "my-secret",
})

_RESOLVER = "sap_cloud_sdk.agent_memory.config.get_resolver"


# ── AgentMemoryConfig ─────────────────────────────────────────────────────────


class TestAgentMemoryConfig:
    def test_raises_when_base_url_empty(self):
        with pytest.raises(AgentMemoryConfigError, match="base_url"):
            AgentMemoryConfig(base_url="")

    def test_raises_when_token_url_empty_string(self):
        with pytest.raises(AgentMemoryConfigError, match="token_url"):
            AgentMemoryConfig(base_url="http://localhost", token_url="")

    def test_raises_when_client_id_empty_string(self):
        with pytest.raises(AgentMemoryConfigError, match="client_id"):
            AgentMemoryConfig(base_url="http://localhost", client_id="")

    def test_raises_when_client_secret_empty_string(self):
        with pytest.raises(AgentMemoryConfigError, match="client_secret"):
            AgentMemoryConfig(base_url="http://localhost", client_secret="")

    def test_optional_fields_default_to_none(self):
        config = AgentMemoryConfig(base_url="http://localhost:8080")
        assert config.token_url is None
        assert config.client_id is None
        assert config.client_secret is None

    def test_timeout_default(self):
        config = AgentMemoryConfig(base_url="http://localhost:8080")
        assert config.timeout == 30.0

    def test_valid_config_with_all_fields_does_not_raise(self):
        AgentMemoryConfig(
            base_url="https://memory.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="my-client",
            client_secret="my-secret",
        )


# ── BindingData ───────────────────────────────────────────────────────────────


class TestBindingData:
    def test_validate_raises_when_application_url_missing(self):
        with pytest.raises(AgentMemoryConfigError, match="application_url"):
            BindingData(application_url="", uaa=_VALID_UAA).validate()

    def test_validate_raises_when_uaa_missing(self):
        with pytest.raises(AgentMemoryConfigError, match="uaa"):
            BindingData(application_url="https://memory.example.com", uaa="").validate()

    def test_validate_passes_when_all_fields_set(self):
        BindingData(application_url="https://memory.example.com", uaa=_VALID_UAA).validate()

    def test_extract_config_maps_url(self):
        config = BindingData(application_url="https://memory.example.com", uaa=_VALID_UAA).extract_config()
        assert config.base_url == "https://memory.example.com"

    def test_extract_config_derives_token_url(self):
        config = BindingData(application_url="https://memory.example.com", uaa=_VALID_UAA).extract_config()
        assert config.token_url == "https://auth.example.com/oauth/token"

    def test_extract_config_strips_trailing_slash_from_uaa_url(self):
        uaa = json.dumps({"url": "https://auth.example.com/", "clientid": "c", "clientsecret": "s"})
        config = BindingData(application_url="https://memory.example.com", uaa=uaa).extract_config()
        assert config.token_url == "https://auth.example.com/oauth/token"

    def test_extract_config_maps_client_credentials(self):
        config = BindingData(application_url="https://memory.example.com", uaa=_VALID_UAA).extract_config()
        assert config.client_id == "my-client"
        assert config.client_secret == "my-secret"

    def test_extract_config_raises_on_invalid_json(self):
        with pytest.raises(AgentMemoryConfigError, match="Failed to parse uaa JSON"):
            BindingData(application_url="https://memory.example.com", uaa="not-json").extract_config()

    def test_extract_config_raises_on_missing_json_key(self):
        uaa = json.dumps({"url": "https://auth.example.com"})  # missing clientid/clientsecret
        with pytest.raises(AgentMemoryConfigError, match="Missing required field in uaa JSON"):
            BindingData(application_url="https://memory.example.com", uaa=uaa).extract_config()

    def test_extract_config_ignores_extra_uaa_fields(self):
        uaa = json.dumps({
            "apiurl": "https://api.authentication.eu12.hana.ondemand.com",
            "clientid": "my-client",
            "clientsecret": "my-secret",
            "credential-type": "binding-secret",
            "identityzone": "my-zone",
            "tenantid": "tenant-123",
            "url": "https://auth.example.com",
            "xsappname": "my-app",
            "zoneid": "1acb547d-6df6-40a6-abb6-e41dd7d079d1",
        })
        config = BindingData(application_url="https://memory.example.com", uaa=uaa).extract_config()
        assert config.base_url == "https://memory.example.com"
        assert config.token_url == "https://auth.example.com/oauth/token"
        assert config.client_id == "my-client"
        assert config.client_secret == "my-secret"

    def test_extract_config_raises_on_empty_uaa_object(self):
        with pytest.raises(AgentMemoryConfigError, match="Missing required field in uaa JSON"):
            BindingData(application_url="https://memory.example.com", uaa="{}").extract_config()


# ── _load_config_from_env ─────────────────────────────────────────────────────


def _fill_binding(module, instance, target) -> None:
    target.application_url = "https://memory.example.com"
    target.uaa = _VALID_UAA


class TestLoadConfigFromEnv:
    def test_success_via_resolver(self):
        with patch(_RESOLVER) as mock_get_resolver:
            mock_get_resolver.return_value.resolve.side_effect = _fill_binding
            config = _load_secrets()

        assert config.base_url == "https://memory.example.com"
        assert config.token_url == "https://auth.example.com/oauth/token"
        assert config.client_id == "my-client"
        assert config.client_secret == "my-secret"

    def test_calls_resolver_with_correct_arguments(self):
        with patch(_RESOLVER) as mock_get_resolver:
            mock_get_resolver.return_value.resolve.side_effect = _fill_binding
            _load_secrets()

        mock_get_resolver.return_value.resolve.assert_called_once_with(
            module="agent_memory", instance="default", target=mock_get_resolver.return_value.resolve.call_args[1]["target"]
        )

    def test_raises_config_error_when_resolver_fails(self):
        with patch(_RESOLVER) as mock_get_resolver:
            mock_get_resolver.return_value.resolve.side_effect = RuntimeError("both sources failed")
            with pytest.raises(AgentMemoryConfigError, match="Failed to load Agent Memory configuration"):
                _load_secrets()

    def test_raises_config_error_when_binding_incomplete(self):
        def partial_fill(module, instance, target):
            target.application_url = "https://memory.example.com"
            # uaa remains empty → validate() raises

        with patch(_RESOLVER) as mock_get_resolver:
            mock_get_resolver.return_value.resolve.side_effect = partial_fill
            with pytest.raises(AgentMemoryConfigError, match="uaa"):
                _load_secrets()

    def test_raises_config_error_when_uaa_json_invalid(self):
        def fill_invalid_uaa(module, instance, target):
            target.application_url = "https://memory.example.com"
            target.uaa = "not-valid-json"

        with patch(_RESOLVER) as mock_get_resolver:
            mock_get_resolver.return_value.resolve.side_effect = fill_invalid_uaa
            with pytest.raises(AgentMemoryConfigError, match="Failed to parse uaa JSON"):
                _load_secrets()
