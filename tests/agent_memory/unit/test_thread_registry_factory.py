"""Unit tests for create_thread_registry() factory."""

import logging
from unittest.mock import patch

import pytest

from sap_cloud_sdk.agent_memory.config import AgentMemoryConfig
from sap_cloud_sdk.agent_memory.exceptions import AgentMemoryConfigError
from sap_cloud_sdk.agent_memory.thread_registry import (
    InMemoryThreadRegistry,
    SAPAgentMemoryThreadRegistry,
)
from sap_cloud_sdk.agent_memory.thread_registry._factory import create_thread_registry

_NO_CREDENTIALS = "sap_cloud_sdk.agent_memory.config._load_config_from_env"
_VALID_CONFIG = AgentMemoryConfig(
    base_url="https://agent-memory.example.com",
    token_url="https://tenant.authentication.region.hana.ondemand.com/oauth/token",
    client_id="client-id",
    client_secret="client-secret",
)


class TestCreateThreadRegistryNoCredentials:
    """create_thread_registry() with no credentials returns InMemoryThreadRegistry."""

    def test_returns_in_memory_when_no_credentials(self):
        result = create_thread_registry()
        assert isinstance(result, InMemoryThreadRegistry)

    def test_ttl_seconds_stored_on_in_memory_registry(self):
        result = create_thread_registry(ttl_seconds=3600)
        assert isinstance(result, InMemoryThreadRegistry)
        assert result._default_ttl == 3600

    def test_no_ttl_default_is_none(self):
        result = create_thread_registry()
        assert isinstance(result, InMemoryThreadRegistry)
        assert result._default_ttl is None

    def test_no_credentials_logs_warning(self, caplog):
        with caplog.at_level(
            logging.WARNING,
            logger="sap_cloud_sdk.agent_memory.thread_registry._factory",
        ):
            create_thread_registry()
        assert "InMemoryThreadRegistry" in caplog.text

    def test_falls_back_to_in_memory_on_no_binding(self):
        with patch(_NO_CREDENTIALS, return_value=None):
            result = create_thread_registry()
        assert isinstance(result, InMemoryThreadRegistry)

    def test_raises_config_error_for_malformed_binding(self):
        with patch(_NO_CREDENTIALS, side_effect=AgentMemoryConfigError("malformed")):
            with pytest.raises(AgentMemoryConfigError, match="malformed"):
                create_thread_registry()


class TestCreateThreadRegistryServicePath:
    """create_thread_registry() with credentials returns SAPAgentMemoryThreadRegistry."""

    def _with_config(self, fn, config=_VALID_CONFIG):
        with patch(_NO_CREDENTIALS, return_value=config):
            return fn()

    def test_returns_sap_registry_when_credentials_present(self):
        result = self._with_config(create_thread_registry)
        assert isinstance(result, SAPAgentMemoryThreadRegistry)

    def test_idle_ttl_forwarded_as_default_on_registry(self):
        result = self._with_config(lambda: create_thread_registry(ttl_seconds=7200))
        assert result._default_ttl == 7200

    def test_returns_sap_registry_for_ias_config(self):
        ias_config = AgentMemoryConfig(base_url="https://agent-memory.example.com")
        result = self._with_config(create_thread_registry, config=ias_config)
        assert isinstance(result, SAPAgentMemoryThreadRegistry)
