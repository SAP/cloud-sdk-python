"""Unit tests for Destination configuration and binding resolution."""

import pytest
from unittest.mock import patch, MagicMock

from sap_cloud_sdk.destination.config import (
    BindingData,
    load_secrets,
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

    @patch("sap_cloud_sdk.destination.config.get_resolver")
    def test_load_success_default_instance(self, mock_get_resolver):
        mock_resolver = MagicMock()

        def fake_resolve(module, instance, target):
            assert isinstance(target, BindingData)
            target.clientid = "cid"
            target.clientsecret = "csecret"
            target.url = "https://auth.example.com"
            target.uri = "https://destination.example.com"
            target.identityzone = "provider-zone"

        mock_resolver.resolve.side_effect = fake_resolve
        mock_get_resolver.return_value = mock_resolver

        sb = load_secrets()
        assert isinstance(sb, DestinationConfig)
        assert sb.url == "https://destination.example.com"
        assert sb.token_url == "https://auth.example.com/oauth/token"
        assert sb.client_id == "cid"
        assert sb.client_secret == "csecret"
        assert sb.identityzone == "provider-zone"

        mock_resolver.resolve.assert_called_once_with(
            module="destination", instance="default", target=mock_resolver.resolve.call_args[1]["target"]
        )

    @patch("sap_cloud_sdk.destination.config.get_resolver")
    def test_load_success_custom_instance(self, mock_get_resolver):
        mock_resolver = MagicMock()

        def fake_resolve(module, instance, target):
            target.clientid = "cid"
            target.clientsecret = "csecret"
            target.url = "https://auth.example.com"
            target.uri = "https://destination.example.com"
            target.identityzone = "provider-zone"

        mock_resolver.resolve.side_effect = fake_resolve
        mock_get_resolver.return_value = mock_resolver

        sb = load_secrets("custom")
        assert isinstance(sb, DestinationConfig)
        mock_resolver.resolve.assert_called_once_with(
            module="destination", instance="custom", target=mock_resolver.resolve.call_args[1]["target"]
        )

    @patch("sap_cloud_sdk.destination.config.get_resolver")
    def test_load_validation_error_propagates_as_config_error(self, mock_get_resolver):
        mock_resolver = MagicMock()

        def fake_resolve(module, instance, target):
            target.clientid = ""
            target.clientsecret = ""
            target.url = ""
            target.uri = ""

        mock_resolver.resolve.side_effect = fake_resolve
        mock_get_resolver.return_value = mock_resolver

        with pytest.raises(ConfigError, match="failed to load destination configuration"):
            load_secrets()

    @patch("sap_cloud_sdk.destination.config.get_resolver")
    def test_load_read_exception_wrapped(self, mock_get_resolver):
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = Exception("Mount read failed")
        mock_get_resolver.return_value = mock_resolver

        with pytest.raises(ConfigError, match="failed to load destination configuration"):
            load_secrets()

    @patch("sap_cloud_sdk.destination.config.get_resolver")
    def test_load_error_message_contains_guidance(self, mock_get_resolver):
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = RuntimeError(
            "module=destination instance=default failed to read secrets from all resolvers: "
            "['MountResolver failed: path does not exist: /etc/secrets/appfnd/destination/default;', "
            "\"EnvVarResolver failed: 'env var not found: CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID';\"] "
            "Options: mount secrets under the service binding path, set environment variables "
            "like CLOUD_SDK_CFG_destination_default_<KEY> (uppercased), or set VCAP_SERVICES."
        )
        mock_get_resolver.return_value = mock_resolver

        with pytest.raises(ConfigError) as excinfo:
            load_secrets()
        msg = str(excinfo.value)
        assert "failed to load destination configuration" in msg
        assert "CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID" in msg
        assert "/etc/secrets/appfnd/destination/default" in msg


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
