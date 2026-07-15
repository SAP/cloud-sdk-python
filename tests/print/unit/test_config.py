"""Unit tests for print module config loading."""

import json
import pytest
from unittest.mock import patch, MagicMock

from sap_cloud_sdk.print.config import PrintConfig, load_secrets
from sap_cloud_sdk.print.exceptions import ConfigError

_RESOLVER = "sap_cloud_sdk.print.config.get_resolver"


def _uaa_json(
    clientid="cid", clientsecret="csecret", url="https://auth.example.com"
) -> str:
    return json.dumps({"clientid": clientid, "clientsecret": clientsecret, "url": url})


class TestLoadFromEnvOrMount:

    @patch(_RESOLVER)
    def test_returns_print_config(self, mock_get_resolver):
        def fill_binding(module, instance, target):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json()

        mock_get_resolver.return_value.resolve.side_effect = fill_binding

        config = load_secrets()

        assert isinstance(config, PrintConfig)
        assert config.url == "https://api.eu10.print.services.sap"
        assert config.client_id == "cid"
        assert config.client_secret == "csecret"
        assert config.token_url == "https://auth.example.com/oauth/token"

    @patch(_RESOLVER)
    def test_uses_default_instance(self, mock_get_resolver):
        def fill_binding(module, instance, target):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json()

        mock_get_resolver.return_value.resolve.side_effect = fill_binding

        load_secrets()
        mock_get_resolver.return_value.resolve.assert_called_once_with(
            module="print", instance="default", target=mock_get_resolver.return_value.resolve.call_args[1]["target"]
        )

    @patch(_RESOLVER)
    def test_uses_provided_instance(self, mock_get_resolver):
        def fill_binding(module, instance, target):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json()

        mock_get_resolver.return_value.resolve.side_effect = fill_binding

        load_secrets(instance="prod")
        mock_get_resolver.return_value.resolve.assert_called_once_with(
            module="print", instance="prod", target=mock_get_resolver.return_value.resolve.call_args[1]["target"]
        )

    @patch(_RESOLVER)
    def test_missing_url_raises_config_error(self, mock_get_resolver):
        def fill_binding(module, instance, target):
            target.url = ""
            target.uaa = _uaa_json()

        mock_get_resolver.return_value.resolve.side_effect = fill_binding

        with pytest.raises(ConfigError, match="failed to load print configuration"):
            load_secrets()

    @patch(_RESOLVER)
    def test_invalid_uaa_json_raises_config_error(self, mock_get_resolver):
        def fill_binding(module, instance, target):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = "not-valid-json"

        mock_get_resolver.return_value.resolve.side_effect = fill_binding

        with pytest.raises(ConfigError):
            load_secrets()

    @patch(_RESOLVER)
    def test_missing_clientid_raises_config_error(self, mock_get_resolver):
        def fill_binding(module, instance, target):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json(clientid="")

        mock_get_resolver.return_value.resolve.side_effect = fill_binding

        with pytest.raises(ConfigError, match="clientid"):
            load_secrets()

    @patch(_RESOLVER)
    def test_missing_clientsecret_raises_config_error(self, mock_get_resolver):
        def fill_binding(module, instance, target):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json(clientsecret="")

        mock_get_resolver.return_value.resolve.side_effect = fill_binding

        with pytest.raises(ConfigError, match="clientsecret"):
            load_secrets()

    @patch(_RESOLVER)
    def test_missing_uaa_url_raises_config_error(self, mock_get_resolver):
        def fill_binding(module, instance, target):
            target.url = "https://api.eu10.print.services.sap"
            target.uaa = _uaa_json(url="")

        mock_get_resolver.return_value.resolve.side_effect = fill_binding

        with pytest.raises(ConfigError, match="uaa.url"):
            load_secrets()
