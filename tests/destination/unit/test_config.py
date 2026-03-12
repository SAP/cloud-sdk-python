"""Unit tests for Destination configuration and binding resolution."""

import pytest
from unittest.mock import patch, MagicMock

from sap_cloud_sdk.destination.config import (
    BindingData,
    load_from_env_or_mount,
    load_transparent_proxy,
    _TRANSPARENT_PROXY_ENV_VAR,
)
from sap_cloud_sdk.destination.config import DestinationConfig
from sap_cloud_sdk.destination._models import TransparentProxy
from sap_cloud_sdk.destination.exceptions import ConfigError


class TestBindingData:

    def test_default_initialization(self):
        b = BindingData()
        assert b.clientid == ""
        assert b.clientsecret == ""
        assert b.url == ""
        assert b.uri == ""
        assert b.identityzone == ""

    def test_validate_success_with_uri_and_url(self):
        b = BindingData(
            clientid="cid",
            clientsecret="csecret",
            url="https://auth.example.com",
            uri="https://destination.example.com",
            identityzone="provider-zone",
        )
        b.validate()  # should not raise

    def test_validate_missing_clientid(self):
        b = BindingData(
            clientid="",
            clientsecret="csecret",
            url="https://auth.example.com",
            uri="https://destination.example.com",
            identityzone="provider-zone",
        )
        with pytest.raises(ValueError, match="clientid is required"):
            b.validate()

    def test_validate_missing_clientsecret(self):
        b = BindingData(
            clientid="cid",
            clientsecret="",
            url="https://auth.example.com",
            uri="https://destination.example.com",
            identityzone="provider-zone",
        )
        with pytest.raises(ValueError, match="clientsecret is required"):
            b.validate()

    def test_validate_missing_uri(self):
        b = BindingData(
            clientid="cid",
            clientsecret="csecret",
            url="https://auth.example.com",
            uri="",
            identityzone="provider-zone",
        )
        with pytest.raises(ValueError, match="uri is required"):
            b.validate()

    def test_validate_missing_auth_base_url(self):
        # Provide service base via uri, but missing url for token construction
        b = BindingData(
            clientid="cid",
            clientsecret="csecret",
            url="",
            uri="https://destination.example.com",
            identityzone="provider-zone",
        )
        with pytest.raises(ValueError, match="url is required"):
            b.validate()

    def test_to_binding_transforms_fields(self):
        b = BindingData(
            clientid="cid",
            clientsecret="csecret",
            url="https://auth.example.com",
            uri="https://destination.example.com",
            identityzone="provider-zone",
        )
        sb = b.to_binding()
        assert isinstance(sb, DestinationConfig)
        # Prefer uri as service base
        assert sb.url == "https://destination.example.com"
        # Token URL constructed from auth base
        assert sb.token_url == "https://auth.example.com/oauth/token"
        # Client credentials propagated
        assert sb.client_id == "cid"
        assert sb.client_secret == "csecret"
        # identityzone preserved
        assert sb.identityzone == "provider-zone"


class TestLoadFromEnvOrMount:

    @patch("sap_cloud_sdk.destination.config.read_from_mount_and_fallback_to_env_var")
    def test_load_success_default_instance(self, mock_read):
        def fake_read_side_effect(*args, **kwargs):
            target = kwargs.get("target")
            assert isinstance(target, BindingData)
            target.clientid = "cid"
            target.clientsecret = "csecret"
            target.url = "https://auth.example.com"
            target.uri = "https://destination.example.com"
            target.identityzone = "provider-zone"

        mock_read.side_effect = fake_read_side_effect

        sb = load_from_env_or_mount()
        assert isinstance(sb, DestinationConfig)
        assert sb.url == "https://destination.example.com"
        assert sb.token_url == "https://auth.example.com/oauth/token"
        assert sb.client_id == "cid"
        assert sb.client_secret == "csecret"
        assert sb.identityzone == "provider-zone"

        # Verify resolver called with expected parameters
        assert mock_read.call_count == 1
        _, kwargs = mock_read.call_args
        assert kwargs["base_volume_mount"] == "/etc/secrets/appfnd"
        assert kwargs["base_var_name"] == "CLOUD_SDK_CFG"
        assert kwargs["module"] == "destination"
        assert kwargs["instance"] == "default"
        assert isinstance(kwargs["target"], BindingData)

    @patch("sap_cloud_sdk.destination.config.read_from_mount_and_fallback_to_env_var")
    def test_load_success_custom_instance(self, mock_read):
        def fake_read_side_effect(*args, **kwargs):
            target = kwargs.get("target")
            target.clientid = "cid"  # ty: ignore[invalid-assignment]
            target.clientsecret = "csecret"  # ty: ignore[invalid-assignment]
            target.url = "https://auth.example.com"  # ty: ignore[invalid-assignment]
            target.uri = "https://destination.example.com"  # ty: ignore[invalid-assignment]
            target.identityzone = "provider-zone"  # ty: ignore[invalid-assignment]

        mock_read.side_effect = fake_read_side_effect

        sb = load_from_env_or_mount("custom")
        assert isinstance(sb, DestinationConfig)
        assert mock_read.call_args[1]["instance"] == "custom"

    @patch("sap_cloud_sdk.destination.config.read_from_mount_and_fallback_to_env_var")
    def test_load_validation_error_propagates_as_config_error(self, mock_read):
        def fake_read_side_effect(*args, **kwargs):
            target = kwargs.get("target")
            # Populate invalid data to trigger BindingData.validate failure
            target.clientid = ""  # ty: ignore[invalid-assignment]
            target.clientsecret = ""  # ty: ignore[invalid-assignment]
            target.url = ""  # ty: ignore[invalid-assignment]
            target.uri = ""  # ty: ignore[invalid-assignment]

        mock_read.side_effect = fake_read_side_effect

        with pytest.raises(ConfigError, match="failed to load destination configuration"):
            load_from_env_or_mount()

    @patch("sap_cloud_sdk.destination.config.read_from_mount_and_fallback_to_env_var")
    def test_load_read_exception_wrapped(self, mock_read):
        mock_read.side_effect = Exception("Mount read failed")
        with pytest.raises(ConfigError, match="failed to load destination configuration"):
            load_from_env_or_mount()

    @patch("sap_cloud_sdk.destination.config.read_from_mount_and_fallback_to_env_var")
    def test_load_error_message_contains_guidance(self, mock_read):
        # Simulate aggregated failure inside the resolver (mount + env fallback) with resolver-style message
        mock_read.side_effect = RuntimeError(
            "module=destination instance=default failed to read secrets: "
            "['mount failed: path does not exist: /etc/secrets/appfnd/destination/default;', "
            "\"env var failed: 'env var not found: CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID';\"] "
            "Secrets could not be loaded from mount or environment. "
            "Options: - If running locally and '/etc/secrets/appfnd' is not available, "
            "- Provide environment variables like CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID. "
            "- Alternatively, mount secrets under /etc/secrets/appfnd/destination/default/ with files for each required key."
        )
        with pytest.raises(ConfigError) as excinfo:
            load_from_env_or_mount()
        msg = str(excinfo.value)
        # Central resolver provides generic actionable guidance
        assert "failed to load destination configuration" in msg
        assert "Secrets could not be loaded from mount or environment." in msg
        assert "Options:" in msg
        # Generic env var prefix for default instance
        assert "CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID" in msg
        assert "CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID" in msg
        # Mount path for default instance should be referenced
        assert "/etc/secrets/appfnd/destination/default/" in msg


class TestLoadTransparentProxy:
    """Test suite for load_transparent_proxy function."""

    @patch.dict("os.environ", {_TRANSPARENT_PROXY_ENV_VAR: "env-proxy.env-namespace"})
    def test_load_from_env_var(self):
        """Test loading from environment variable."""
        result = load_transparent_proxy()
        
        assert result is not None
        assert result.proxy_name == "env-proxy"
        assert result.namespace == "env-namespace"

    @patch.dict("os.environ", {}, clear=True)
    def test_load_no_proxy_configured(self):
        """Test loading when no proxy is configured returns None."""
        result = load_transparent_proxy()
        assert result is None

    @patch.dict("os.environ", {_TRANSPARENT_PROXY_ENV_VAR: "invalid-format"})
    def test_load_malformed_env_var_single_part(self):
        """Test loading with malformed environment variable (single part) raises ConfigError."""
        with pytest.raises(ConfigError, match="invalid transparent proxy format"):
            load_transparent_proxy()

    @patch.dict("os.environ", {_TRANSPARENT_PROXY_ENV_VAR: "proxy."})
    def test_load_malformed_env_var_empty_namespace(self):
        """Test loading with environment variable having empty namespace after dot raises ConfigError."""
        with pytest.raises(ConfigError, match="invalid transparent proxy format"):
            load_transparent_proxy()

    @patch.dict("os.environ", {_TRANSPARENT_PROXY_ENV_VAR: ".namespace"})
    def test_load_malformed_env_var_empty_proxy_name(self):
        """Test loading with environment variable having empty proxy name before dot raises ConfigError."""
        with pytest.raises(ConfigError, match="invalid transparent proxy format"):
            load_transparent_proxy()

    @patch.dict("os.environ", {_TRANSPARENT_PROXY_ENV_VAR: "proxy.namespace.extra"})
    def test_load_env_var_with_multiple_dots(self):
        """Test loading with environment variable containing multiple dots uses first two parts."""
        result = load_transparent_proxy()
        
        assert result is not None
        assert result.proxy_name == "proxy"
        assert result.namespace == "namespace"
