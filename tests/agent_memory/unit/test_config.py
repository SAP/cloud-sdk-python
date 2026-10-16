"""Unit tests for AgentMemoryConfig, BindingData, and _load_config_from_env."""

import json
from unittest.mock import patch

import pytest

from sap_cloud_sdk.agent_memory.config import (
    AgentMemoryConfig,
    BindingData,
    _load_config_from_env,
)
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryConfigError

_VALID_UAA = json.dumps(
    {
        "url": "https://auth.example.com",
        "clientid": "my-client",
        "clientsecret": "my-secret",
    }
)

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

    def test_raises_when_identityzone_set_without_token_url(self):
        # identityzone is XSUAA-only (derives the subscriber token URL); it must
        # not be set in IAS mode (no token_url/client_id/client_secret).
        with pytest.raises(AgentMemoryConfigError, match="identityzone applies only to XSUAA"):
            AgentMemoryConfig(base_url="http://localhost", identityzone="my-zone")

    def test_identityzone_allowed_with_full_xsuaa_credentials(self):
        config = AgentMemoryConfig(
            base_url="https://memory.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="my-client",
            client_secret="my-secret",
            identityzone="my-zone",
        )
        assert config.identityzone == "my-zone"
        assert config.auth_mode == "xsuaa"

    def test_valid_config_with_all_fields_does_not_raise(self):
        AgentMemoryConfig(
            base_url="https://memory.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="my-client",
            client_secret="my-secret",
        )

    def test_auth_mode_derived_as_ias_when_no_token_url(self):
        config = AgentMemoryConfig(base_url="http://localhost:3000")
        assert config.auth_mode == "ias"

    def test_auth_mode_derived_as_xsuaa_when_token_url_present(self):
        config = AgentMemoryConfig(
            base_url="https://memory.example.com",
            token_url="https://auth.example.com/oauth/token",
            client_id="my-client",
            client_secret="my-secret",
        )
        assert config.auth_mode == "xsuaa"

    def test_auth_mode_is_read_only(self):
        # auth_mode is a computed property, never a settable/stored field, so it
        # can never contradict the credentials.
        config = AgentMemoryConfig(base_url="http://localhost:3000")
        with pytest.raises(AttributeError):
            config.auth_mode = "xsuaa"  # type: ignore[misc]
        with pytest.raises(TypeError):
            AgentMemoryConfig(base_url="http://localhost:3000", auth_mode="xsuaa")  # type: ignore[call-arg]


# ── BindingData ───────────────────────────────────────────────────────────────


class TestBindingData:
    def test_validate_raises_when_application_url_missing(self):
        with pytest.raises(AgentMemoryConfigError, match="application_url"):
            BindingData(application_url="", uaa=_VALID_UAA).validate()

    def test_validate_passes_when_uaa_absent(self):
        # URL-only IAS binding: no uaa required
        BindingData(application_url="https://memory.example.com", uaa="").validate()

    def test_validate_passes_when_uaa_none(self):
        # None is the canonical "absent" value for the Optional[str] field
        BindingData(application_url="https://memory.example.com", uaa=None).validate()

    def test_uaa_defaults_to_none(self):
        # Resolver leaves uaa=None when only APPLICATION_URL is present (IAS mode)
        binding = BindingData(application_url="https://memory.example.com")
        assert binding.uaa is None

    def test_validate_passes_when_all_fields_set(self):
        BindingData(
            application_url="https://memory.example.com", uaa=_VALID_UAA
        ).validate()

    def test_extract_config_maps_url(self):
        config = BindingData(
            application_url="https://memory.example.com", uaa=_VALID_UAA
        ).extract_config()
        assert config.base_url == "https://memory.example.com"

    def test_extract_config_derives_token_url(self):
        config = BindingData(
            application_url="https://memory.example.com", uaa=_VALID_UAA
        ).extract_config()
        assert config.token_url == "https://auth.example.com/oauth/token"

    def test_extract_config_sets_xsuaa_auth_mode_when_uaa_present(self):
        config = BindingData(
            application_url="https://memory.example.com", uaa=_VALID_UAA
        ).extract_config()
        assert config.auth_mode == "xsuaa"

    def test_extract_config_strips_trailing_slash_from_uaa_url(self):
        uaa = json.dumps(
            {"url": "https://auth.example.com/", "clientid": "c", "clientsecret": "s"}
        )
        config = BindingData(
            application_url="https://memory.example.com", uaa=uaa
        ).extract_config()
        assert config.token_url == "https://auth.example.com/oauth/token"

    def test_extract_config_maps_client_credentials(self):
        config = BindingData(
            application_url="https://memory.example.com", uaa=_VALID_UAA
        ).extract_config()
        assert config.client_id == "my-client"
        assert config.client_secret == "my-secret"

    def test_extract_config_raises_on_invalid_json(self):
        with pytest.raises(AgentMemoryConfigError, match="Failed to parse uaa JSON"):
            BindingData(
                application_url="https://memory.example.com", uaa="not-json"
            ).extract_config()

    def test_extract_config_raises_on_missing_json_key(self):
        uaa = json.dumps(
            {"url": "https://auth.example.com"}
        )  # missing clientid/clientsecret
        with pytest.raises(
            AgentMemoryConfigError, match="Missing required field in uaa JSON"
        ):
            BindingData(
                application_url="https://memory.example.com", uaa=uaa
            ).extract_config()

    def test_extract_config_maps_identityzone_when_present(self):
        uaa = json.dumps(
            {
                "url": "https://my-zone.authentication.eu12.hana.ondemand.com",
                "clientid": "c",
                "clientsecret": "s",
                "identityzone": "my-zone",
            }
        )
        config = BindingData(
            application_url="https://memory.example.com", uaa=uaa
        ).extract_config()
        assert config.identityzone == "my-zone"

    def test_extract_config_identityzone_is_none_when_absent(self):
        config = BindingData(
            application_url="https://memory.example.com", uaa=_VALID_UAA
        ).extract_config()
        assert config.identityzone is None

    def test_extract_config_ignores_extra_uaa_fields(self):
        uaa = json.dumps(
            {
                "apiurl": "https://api.authentication.eu12.hana.ondemand.com",
                "clientid": "my-client",
                "clientsecret": "my-secret",
                "credential-type": "binding-secret",
                "identityzone": "my-zone",
                "tenantid": "tenant-123",
                "url": "https://auth.example.com",
                "xsappname": "my-app",
                "zoneid": "1acb547d-6df6-40a6-abb6-e41dd7d079d1",
            }
        )
        config = BindingData(
            application_url="https://memory.example.com", uaa=uaa
        ).extract_config()
        assert config.base_url == "https://memory.example.com"
        assert config.token_url == "https://auth.example.com/oauth/token"
        assert config.client_id == "my-client"
        assert config.client_secret == "my-secret"
        assert config.identityzone == "my-zone"

    def test_extract_config_raises_on_empty_uaa_object(self):
        with pytest.raises(
            AgentMemoryConfigError, match="Missing required field in uaa JSON"
        ):
            BindingData(
                application_url="https://memory.example.com", uaa="{}"
            ).extract_config()

    def test_extract_config_url_only_when_uaa_absent(self):
        # URL-only IAS binding: returns base_url-only config, OAuth2 fields None
        config = BindingData(
            application_url="https://memory.example.com", uaa=""
        ).extract_config()
        assert config.base_url == "https://memory.example.com"
        assert config.token_url is None
        assert config.client_id is None
        assert config.client_secret is None

    def test_extract_config_sets_ias_auth_mode_when_uaa_absent(self):
        config = BindingData(
            application_url="https://memory.example.com", uaa=""
        ).extract_config()
        assert config.auth_mode == "ias"
        # None is the canonical absent value after the Optional[str] migration
        config = BindingData(
            application_url="https://memory.example.com", uaa=None
        ).extract_config()
        assert config.base_url == "https://memory.example.com"
        assert config.token_url is None
        assert config.client_id is None
        assert config.client_secret is None

    def test_extract_config_url_only_when_uaa_uses_default(self):
        # No uaa argument at all — field defaults to None
        config = BindingData(
            application_url="https://memory.example.com"
        ).extract_config()
        assert config.base_url == "https://memory.example.com"
        assert config.token_url is None


# ── _load_config_from_env ─────────────────────────────────────────────────────


def _fill_binding(**kwargs) -> None:
    target = kwargs["target"]
    target.application_url = "https://memory.example.com"
    target.uaa = _VALID_UAA


class TestLoadConfigFromEnv:
    def test_success_via_resolver(self):
        with patch(_RESOLVER, side_effect=_fill_binding):
            config = _load_config_from_env()

        assert config is not None
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
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL",
            "https://memory.example.com",
        )
        monkeypatch.setenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA", _VALID_UAA)

        # Let the real resolver run — mount will fail, env vars will succeed
        with patch("os.stat", side_effect=FileNotFoundError("no mount")):
            config = _load_config_from_env()

        assert config is not None
        assert config.base_url == "https://memory.example.com"
        assert config.client_id == "my-client"

    def test_returns_none_when_no_binding_found(self):
        with patch(
            _RESOLVER, return_value=None
        ):  # resolver fills nothing → both fields stay ""
            result = _load_config_from_env()
        assert result is None

    def test_returns_none_when_resolver_finds_no_credentials(self):
        # RuntimeError from the resolver means "no credentials configured anywhere".
        # _load_config_from_env must return None so the factory falls back to
        # InMemory — the factory checks `if config is not None` and has no
        # try/except around _load_config_from_env(), so raising here would crash it.
        with patch(_RESOLVER, side_effect=RuntimeError("both sources failed")):
            result = _load_config_from_env()
        assert result is None

    def test_raises_config_error_when_binding_incomplete(self):
        def partial_fill(**kwargs):
            # application_url missing → validate() raises
            kwargs["target"].uaa = _VALID_UAA

        with patch(_RESOLVER, side_effect=partial_fill):
            with pytest.raises(AgentMemoryConfigError, match="application_url"):
                _load_config_from_env()

    def test_load_config_from_env_url_only_binding(self):
        def fill_url_only(**kwargs):
            kwargs["target"].application_url = "https://memory.example.com"
            # uaa intentionally absent — IAS mode

        with patch(_RESOLVER, side_effect=fill_url_only):
            config = _load_config_from_env()

        assert config is not None
        assert config.base_url == "https://memory.example.com"
        assert config.token_url is None
        assert config.client_id is None

    def test_raises_config_error_when_uaa_json_invalid(self, monkeypatch):
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL",
            "https://memory.example.com",
        )
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA", "not-valid-json"
        )

        with patch("os.stat", side_effect=FileNotFoundError("no mount")):
            with pytest.raises(
                AgentMemoryConfigError, match="Failed to parse uaa JSON"
            ):
                _load_config_from_env()

    def test_ias_url_only_from_env_vars(self, monkeypatch):
        # IAS binding: only APPLICATION_URL env var present, no UAA — real resolver path
        monkeypatch.setenv(
            "CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_APPLICATION_URL",
            "https://memory.example.com",
        )
        # Ensure UAA is absent even if set in the outer environment
        monkeypatch.delenv("CLOUD_SDK_CFG_HANA_AGENT_MEMORY_DEFAULT_UAA", raising=False)

        with patch("os.stat", side_effect=FileNotFoundError("no mount")):
            config = _load_config_from_env()

        assert config is not None
        assert config.base_url == "https://memory.example.com"
        assert config.token_url is None
        assert config.client_id is None
        assert config.client_secret is None
