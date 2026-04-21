"""Unit tests for the Temporal configuration module."""

import os
from unittest.mock import patch

import pytest

from sap_cloud_sdk.temporal.config import TemporalConfig, resolve_config
from sap_cloud_sdk.temporal.exceptions import ConfigurationError


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Remove all Temporal-related env vars before each test."""
    for var in (
        "TEMPORAL_CALL_URL",
        "TEMPORAL_NAMESPACE",
        "WORKLOAD_API_SOCKET",
        "SPIFFE_ENDPOINT_SOCKET",
        "APPFND_LOCALDEV_TEMPORAL",
    ):
        monkeypatch.delenv(var, raising=False)


class TestLocalDevMode:
    def test_localdev_uses_defaults(self, monkeypatch):
        monkeypatch.setenv("APPFND_LOCALDEV_TEMPORAL", "true")
        config = resolve_config()
        assert config.target == "localhost:7233"
        assert config.namespace == "default"
        assert config.is_local_dev is True
        assert config.spiffe_socket_path is None

    def test_localdev_respects_env_vars(self, monkeypatch):
        monkeypatch.setenv("APPFND_LOCALDEV_TEMPORAL", "true")
        monkeypatch.setenv("TEMPORAL_CALL_URL", "myhost:7233")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "my-ns")
        config = resolve_config()
        assert config.target == "myhost:7233"
        assert config.namespace == "my-ns"

    def test_localdev_explicit_args_take_precedence(self, monkeypatch):
        monkeypatch.setenv("APPFND_LOCALDEV_TEMPORAL", "true")
        monkeypatch.setenv("TEMPORAL_CALL_URL", "envhost:7233")
        config = resolve_config(target="arghost:7233", namespace="arg-ns")
        assert config.target == "arghost:7233"
        assert config.namespace == "arg-ns"

    def test_localdev_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("APPFND_LOCALDEV_TEMPORAL", "TRUE")
        config = resolve_config()
        assert config.is_local_dev is True


class TestProductionMode:
    def test_missing_call_url_raises(self):
        with pytest.raises(ConfigurationError, match="TEMPORAL_CALL_URL"):
            resolve_config()

    def test_missing_namespace_raises(self, monkeypatch):
        monkeypatch.setenv("TEMPORAL_CALL_URL", "host:443")
        with pytest.raises(ConfigurationError, match="TEMPORAL_NAMESPACE"):
            resolve_config()

    def test_missing_socket_raises(self, monkeypatch):
        monkeypatch.setenv("TEMPORAL_CALL_URL", "host:443")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "my-ns")
        with pytest.raises(ConfigurationError, match="SPIFFE"):
            resolve_config()

    def test_workload_api_socket_env(self, monkeypatch):
        monkeypatch.setenv("TEMPORAL_CALL_URL", "host:443")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "my-ns")
        monkeypatch.setenv("WORKLOAD_API_SOCKET", "/custom/spire.sock")
        config = resolve_config()
        assert config.spiffe_socket_path == "/custom/spire.sock"
        assert config.is_local_dev is False

    def test_spiffe_endpoint_socket_env(self, monkeypatch):
        monkeypatch.setenv("TEMPORAL_CALL_URL", "host:443")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "my-ns")
        monkeypatch.setenv("SPIFFE_ENDPOINT_SOCKET", "unix:///tmp/spire.sock")
        config = resolve_config()
        assert config.spiffe_socket_path == "/tmp/spire.sock"

    def test_workload_socket_takes_precedence_over_spiffe_socket(self, monkeypatch):
        monkeypatch.setenv("TEMPORAL_CALL_URL", "host:443")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "my-ns")
        monkeypatch.setenv("WORKLOAD_API_SOCKET", "/workload.sock")
        monkeypatch.setenv("SPIFFE_ENDPOINT_SOCKET", "unix:///spiffe.sock")
        config = resolve_config()
        assert config.spiffe_socket_path == "/workload.sock"

    def test_explicit_args_override_env(self, monkeypatch):
        monkeypatch.setenv("TEMPORAL_CALL_URL", "envhost:443")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "env-ns")
        monkeypatch.setenv("WORKLOAD_API_SOCKET", "/spire.sock")
        config = resolve_config(target="arghost:443", namespace="arg-ns")
        assert config.target == "arghost:443"
        assert config.namespace == "arg-ns"

    def test_kyma_socket_discovered(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TEMPORAL_CALL_URL", "host:443")
        monkeypatch.setenv("TEMPORAL_NAMESPACE", "my-ns")
        kyma_sock = tmp_path / "spire-agent.sock"
        kyma_sock.touch()
        with patch(
            "sap_cloud_sdk.temporal.config._K8S_SOCKET", str(kyma_sock)
        ):
            config = resolve_config()
        assert config.spiffe_socket_path == str(kyma_sock)


class TestTemporalConfig:
    def test_frozen_dataclass(self):
        config = TemporalConfig(target="host:443", namespace="ns")
        with pytest.raises(Exception):
            config.target = "other"  # type: ignore[misc]

    def test_default_values(self):
        config = TemporalConfig(target="host:443", namespace="ns")
        assert config.is_local_dev is False
        assert config.spiffe_socket_path is None
