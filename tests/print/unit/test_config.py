"""Unit tests for print module config loading."""

import json
import pytest
from unittest.mock import patch

from sap_cloud_sdk.print.config import PrintConfig, load_from_env_or_mount
from sap_cloud_sdk.print.exceptions import ConfigError


def _uaa_json(
    clientid="cid", clientsecret="csecret", url="https://auth.example.com"
) -> str:
    return json.dumps({"clientid": clientid, "clientsecret": clientsecret, "url": url})


class TestLoadFromEnvOrMount:

    @patch("sap_cloud_sdk.print.config.read_from_mount_and_fallback_to_env_var")
    def test_returns_print_config(self, mock_resolver):
        def fill_binding(*, target, **_):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json()

        mock_resolver.side_effect = fill_binding

        config = load_from_env_or_mount()

        assert isinstance(config, PrintConfig)
        assert config.url == "https://api.eu10.print.services.sap"
        assert config.client_id == "cid"
        assert config.client_secret == "csecret"
        assert config.token_url == "https://auth.example.com/oauth/token"

    @patch("sap_cloud_sdk.print.config.read_from_mount_and_fallback_to_env_var")
    def test_uses_default_instance(self, mock_resolver):
        calls = []

        def capture(**kwargs):
            calls.append(kwargs)
            kwargs["target"].url = "https://api.eu10.print.services.sap"
            kwargs["target"].uaa = _uaa_json()

        mock_resolver.side_effect = capture

        load_from_env_or_mount()
        assert calls[0]["instance"] == "default"

    @patch("sap_cloud_sdk.print.config.read_from_mount_and_fallback_to_env_var")
    def test_uses_provided_instance(self, mock_resolver):
        calls = []

        def capture(**kwargs):
            calls.append(kwargs)
            kwargs["target"].url = "https://api.eu10.print.services.sap"
            kwargs["target"].uaa = _uaa_json()

        mock_resolver.side_effect = capture

        load_from_env_or_mount(instance="prod")
        assert calls[0]["instance"] == "prod"

    @patch("sap_cloud_sdk.print.config.read_from_mount_and_fallback_to_env_var")
    def test_missing_url_raises_config_error(self, mock_resolver):
        def fill_binding(*, target, **_):
            target.url = ""
            target.uaa = _uaa_json()

        mock_resolver.side_effect = fill_binding

        with pytest.raises(ConfigError, match="failed to load print configuration"):
            load_from_env_or_mount()

    @patch("sap_cloud_sdk.print.config.read_from_mount_and_fallback_to_env_var")
    def test_invalid_uaa_json_raises_config_error(self, mock_resolver):
        def fill_binding(*, target, **_):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = "not-valid-json"

        mock_resolver.side_effect = fill_binding

        with pytest.raises(ConfigError):
            load_from_env_or_mount()

    @patch("sap_cloud_sdk.print.config.read_from_mount_and_fallback_to_env_var")
    def test_missing_clientid_raises_config_error(self, mock_resolver):
        def fill_binding(*, target, **_):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json(clientid="")

        mock_resolver.side_effect = fill_binding

        with pytest.raises(ConfigError, match="clientid"):
            load_from_env_or_mount()

    @patch("sap_cloud_sdk.print.config.read_from_mount_and_fallback_to_env_var")
    def test_missing_clientsecret_raises_config_error(self, mock_resolver):
        def fill_binding(*, target, **_):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json(clientsecret="")

        mock_resolver.side_effect = fill_binding

        with pytest.raises(ConfigError, match="clientsecret"):
            load_from_env_or_mount()

    @patch("sap_cloud_sdk.print.config.read_from_mount_and_fallback_to_env_var")
    def test_missing_uaa_url_raises_config_error(self, mock_resolver):
        def fill_binding(*, target, **_):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json(url="")

        mock_resolver.side_effect = fill_binding

        with pytest.raises(ConfigError, match="uaa.url"):
            load_from_env_or_mount()
