"""Unit tests for ClientConfig."""

import os
from unittest.mock import patch

import pytest

from sap_cloud_sdk.agentgateway import ClientConfig, create_client
from sap_cloud_sdk.agentgateway.config import TlsMode


class TestClientConfig:
    """Tests for ClientConfig dataclass."""

    def test_default_values(self):
        """ClientConfig has sensible defaults."""
        config = ClientConfig()
        assert config.timeout == 60.0
        assert config.fallback_token_ttl_seconds == 300.0
        assert config.token_expiry_buffer_seconds == 30.0
        assert config.max_system_token_cache_size == 32
        assert config.max_user_token_cache_size == 256

    def test_custom_timeout(self):
        """ClientConfig accepts custom timeout."""
        config = ClientConfig(timeout=120.0)
        assert config.timeout == 120.0

    def test_create_client_with_config(self):
        """create_client accepts a ClientConfig."""
        config = ClientConfig(timeout=90.0, fallback_token_ttl_seconds=90.0)
        client = create_client(config=config)
        assert client._config.timeout == 90.0
        assert client._config.fallback_token_ttl_seconds == 90.0

    def test_create_client_without_config_uses_defaults(self):
        """create_client uses default config when none provided."""
        client = create_client()
        assert client._config.timeout == 60.0

    def test_default_tls_mode_is_standard(self):
        """Default tls_mode is STANDARD."""
        config = ClientConfig()
        assert config.tls_mode == TlsMode.STANDARD

    def test_explicit_transparent_tls_mode(self):
        """ClientConfig accepts TRANSPARENT tls_mode."""
        config = ClientConfig(tls_mode=TlsMode.TRANSPARENT)
        assert config.tls_mode == TlsMode.TRANSPARENT


class TestClientConfigFromEnv:
    """Tests for ClientConfig.from_env()."""

    def test_from_env_defaults_to_standard(self):
        """from_env() returns STANDARD when AGW_TLS_MODE is unset."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGW_TLS_MODE", None)
            config = ClientConfig.from_env()
        assert config.tls_mode == TlsMode.STANDARD

    def test_from_env_transparent(self):
        """from_env() returns TRANSPARENT when AGW_TLS_MODE=transparent."""
        with patch.dict(os.environ, {"AGW_TLS_MODE": "transparent"}):
            config = ClientConfig.from_env()
        assert config.tls_mode == TlsMode.TRANSPARENT

    def test_from_env_transparent_case_insensitive(self):
        """AGW_TLS_MODE comparison is case-insensitive."""
        with patch.dict(os.environ, {"AGW_TLS_MODE": "TRANSPARENT"}):
            config = ClientConfig.from_env()
        assert config.tls_mode == TlsMode.TRANSPARENT

    def test_from_env_unknown_value_falls_back_to_standard(self):
        """Unknown AGW_TLS_MODE value falls back to STANDARD."""
        with patch.dict(os.environ, {"AGW_TLS_MODE": "unknown"}):
            config = ClientConfig.from_env()
        assert config.tls_mode == TlsMode.STANDARD
