"""Tests for extensibility configuration."""

from sap_cloud_sdk.extensibility.config import ExtensibilityConfig


class TestExtensibilityConfig:
    """Tests for ExtensibilityConfig dataclass."""

    def test_defaults(self):
        config = ExtensibilityConfig()
        assert config.destination_name is None
        assert config.destination_instance == "default"

    def test_custom_destination_name(self):
        config = ExtensibilityConfig(destination_name="MY_CUSTOM_DEST")
        assert config.destination_name == "MY_CUSTOM_DEST"
        assert config.destination_instance == "default"

    def test_custom_destination_instance(self):
        config = ExtensibilityConfig(destination_instance="production")
        assert config.destination_name is None
        assert config.destination_instance == "production"

    def test_fully_custom(self):
        config = ExtensibilityConfig(
            destination_name="EXT_BACKEND_V2",
            destination_instance="staging",
        )
        assert config.destination_name == "EXT_BACKEND_V2"
        assert config.destination_instance == "staging"

    def test_equality(self):
        c1 = ExtensibilityConfig()
        c2 = ExtensibilityConfig()
        assert c1 == c2

    def test_inequality(self):
        c1 = ExtensibilityConfig()
        c2 = ExtensibilityConfig(destination_name="OTHER")
        assert c1 != c2
