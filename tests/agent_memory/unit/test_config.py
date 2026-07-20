"""Unit tests for AgentMemoryConfig, BindingData, _load_config_from_env, and _load_config_for_instance."""

import json
from unittest.mock import patch

import pytest

from sap_cloud_sdk.agent_memory.config import (
    AgentMemoryConfig,
    BindingData,
    _load_config_for_instance,
    _load_config_from_env,
)
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryConfigError

_VALID_UAA = json.dumps({
    "url": "https://auth.example.com",
    "clientid": "my-client",
    "clientsecret": "my-secret",
})

_RESOLVER = "sap_cloud_sdk.core.secret_resolver.read_from_mount_and_fallback_to_env_var"


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

    def test_raises_when_identityzone_empty_string(self):
        with pytest.raises(AgentMemoryConfigError, match="identityzone"):
            AgentMemoryConfig(base_url="http://localhost", identityzone="")

    def test_identityzone_defaults_to_none(self):
        config = AgentMemoryConfig(base_url="http://localhost:8080")
        assert config.identityzone is None

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

    def test_extract_config_maps_identityzone_when_present(self):
        uaa = json.dumps({
            "url": "https://my-zone.authentication.eu12.hana.ondemand.com",
            "clientid": "c",
            "clientsecret": "s",
            "identityzone": "my-zone",
        })
        config = BindingData(application_url="https://memory.example.com", uaa=uaa).extract_config()
        assert config.identityzone == "my-zone"

    def test_extract_config_identityzone_is_none_when_absent(self):
        config = BindingData(application_url="https://memory.example.com", uaa=_VALID_UAA).extract_config()
        assert config.identityzone is None

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
        assert config.identityzone == "my-zone"

    def test_extract_config_raises_on_empty_uaa_object(self):
        with pytest.raises(AgentMemoryConfigError, match="Missing required field in uaa JSON"):
            BindingData(application_url="https://memory.example.com", uaa="{}").extract_config()


# ── _load_config_from_env ─────────────────────────────────────────────────────


def _fill_binding(**kwargs) -> None:
    target = kwargs["target"]
    target.application_url = "https://memory.example.com"
    target.uaa = _VALID_UAA


class TestLoadConfigFromEnv:
    def test_success_via_resolver(self):
        with patch(_RESOLVER, side_effect=_fill_binding):
            config = _load_config_from_env()

        assert config.base_url == "https://memory.example.com"
        assert config.token_url == "https://auth.example.com/oauth/token"
        assert config.client_id == "my-client"
        assert config.client_secret == "my-secret"

    def test_calls_resolver_with_correct_arguments(self):
        with patch(_RESOLVER, side_effect=_fill_binding) as mock_resolver:
            _load_config_from_env()

        mock_resolver.assert_called_once()
        _, kwargs = mock_resolver.call_args
        assert kwargs["base_volume_mount"] == "/etc/secrets/appfnd"
        assert kwargs["base_var_name"] == "CLOUD_SDK_CFG"
        assert kwargs["module"] == "hana-agent-memory"
        assert kwargs["instance"] == "default"

    def test_falls_back_to_env_vars(self, monkeypatch):
        monkeypatch.setenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL", "https://memory.example.com")
        monkeypatch.setenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA", _VALID_UAA)

        # Let the real resolver run — mount will fail, env vars will succeed
        with patch("os.stat", side_effect=FileNotFoundError("no mount")):
            config = _load_config_from_env()

        assert config.base_url == "https://memory.example.com"
        assert config.client_id == "my-client"

    def test_raises_config_error_when_resolver_fails(self):
        with patch(_RESOLVER, side_effect=RuntimeError("both sources failed")):
            with pytest.raises(AgentMemoryConfigError, match="Failed to load Agent Memory configuration"):
                _load_config_from_env()

    def test_raises_config_error_when_binding_incomplete(self):
        def partial_fill(**kwargs):
            kwargs["target"].application_url = "https://memory.example.com"
            # uaa remains empty → validate() raises

        with patch(_RESOLVER, side_effect=partial_fill):
            with pytest.raises(AgentMemoryConfigError, match="uaa"):
                _load_config_from_env()

    def test_raises_config_error_when_uaa_json_invalid(self, monkeypatch):
        monkeypatch.setenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL", "https://memory.example.com")
        monkeypatch.setenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA", "not-valid-json")

        with patch("os.stat", side_effect=FileNotFoundError("no mount")):
            with pytest.raises(AgentMemoryConfigError, match="Failed to parse uaa JSON"):
                _load_config_from_env()


# ── _load_config_for_instance ─────────────────────────────────────────────────


def _fill_binding_for_instance(instance_name: str):
    """Return a side_effect that fills binding only when instance matches."""
    def _fill(**kwargs):
        assert kwargs["instance"] == instance_name
        kwargs["target"].application_url = f"https://{instance_name}.memory.example.com"
        kwargs["target"].uaa = json.dumps({
            "url": f"https://{instance_name}.auth.example.com",
            "clientid": f"{instance_name}-client",
            "clientsecret": "secret",
        })
    return _fill


class TestLoadConfigForInstance:

    def test_loads_named_instance_binding(self):
        """Loads config from the specified instance name (not 'default')."""
        with patch(_RESOLVER, side_effect=_fill_binding_for_instance("acme-corp")):
            config = _load_config_for_instance("acme-corp")

        assert config.base_url == "https://acme-corp.memory.example.com"
        assert config.token_url == "https://acme-corp.auth.example.com/oauth/token"
        assert config.client_id == "acme-corp-client"

    def test_calls_resolver_with_correct_instance(self):
        """Resolver receives the exact instance name passed (not 'default')."""
        with patch(_RESOLVER, side_effect=_fill_binding_for_instance("beta-tenant")) as mock_resolver:
            _load_config_for_instance("beta-tenant")

        _, kwargs = mock_resolver.call_args
        assert kwargs["module"] == "hana-agent-memory"
        assert kwargs["instance"] == "beta-tenant"

    def test_default_instance_is_equivalent_to_load_config_from_env(self):
        """_load_config_for_instance('default') produces the same result as _load_config_from_env."""
        with patch(_RESOLVER, side_effect=_fill_binding_for_instance("default")):
            config_instance = _load_config_for_instance("default")
        with patch(_RESOLVER, side_effect=_fill_binding_for_instance("default")):
            config_env = _load_config_from_env()

        assert config_instance.base_url == config_env.base_url
        assert config_instance.token_url == config_env.token_url

    def test_raises_with_instance_name_in_message_when_binding_missing(self):
        """Error message includes the instance name when the binding cannot be loaded."""
        with patch(_RESOLVER, side_effect=RuntimeError("secrets not found")):
            with pytest.raises(AgentMemoryConfigError, match="acme-corp"):
                _load_config_for_instance("acme-corp")

    def test_loads_from_env_vars_for_named_instance(self, monkeypatch):
        """Subscriber binding loaded from env vars keyed by tenant name."""
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_ACME_CORP_APPLICATION_URL",
            "https://acme-corp.memory.example.com",
        )
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_ACME_CORP_UAA",
            json.dumps({
                "url": "https://acme-corp.auth.example.com",
                "clientid": "acme-client",
                "clientsecret": "secret",
            }),
        )

        with patch("os.stat", side_effect=FileNotFoundError("no mount")):
            config = _load_config_for_instance("acme-corp")

        assert config.base_url == "https://acme-corp.memory.example.com"
        assert config.client_id == "acme-client"
