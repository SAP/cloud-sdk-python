"""Tests for NoOpTransport."""

from sap_cloud_sdk.extensibility._noop_transport import NoOpTransport
from sap_cloud_sdk.extensibility._models import ExtensionCapabilityImplementation


class TestNoOpTransport:
    """Tests for NoOpTransport."""

    def test_returns_empty_result(self):
        """Test that NoOpTransport returns an empty ExtensionCapabilityImplementation."""
        transport = NoOpTransport()
        result = transport.get_extension_capability_implementation()

        assert isinstance(result, ExtensionCapabilityImplementation)
        assert result.capability_id == "default"
        assert result.mcp_servers == []
        assert result.instruction is None
        assert result.extension_names == []
        assert result.hooks == []

    def test_custom_capability_id(self):
        """Test that NoOpTransport passes through the capability_id."""
        transport = NoOpTransport()
        result = transport.get_extension_capability_implementation(
            capability_id="custom"
        )

        assert result.capability_id == "custom"
        assert result.mcp_servers == []
        assert result.hooks == []
