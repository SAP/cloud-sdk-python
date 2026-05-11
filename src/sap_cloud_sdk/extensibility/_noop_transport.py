"""No-op transport for graceful degradation.

Used by :func:`create_client` when the live transport cannot be
constructed (e.g. missing destination credentials in local development).
Ensures the agent can always start and operate with its built-in tools.
"""

from __future__ import annotations

from sap_cloud_sdk.extensibility._models import (
    DEFAULT_EXTENSION_CAPABILITY_ID,
    ExtensionCapabilityImplementation,
)


class NoOpTransport:
    """Fallback transport that always returns empty results."""

    def get_extension_capability_implementation(
        self,
        capability_id: str = DEFAULT_EXTENSION_CAPABILITY_ID,
        skip_cache: bool = False,
        tenant: str = "",
    ) -> ExtensionCapabilityImplementation:
        return ExtensionCapabilityImplementation(capability_id=capability_id)
