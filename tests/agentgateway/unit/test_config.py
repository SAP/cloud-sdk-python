"""Unit tests for ClientConfig."""

from sap_cloud_sdk.agentgateway import ClientConfig, create_client


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
