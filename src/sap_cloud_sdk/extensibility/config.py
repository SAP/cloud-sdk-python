"""Configuration for the extensibility module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtensibilityConfig:
    """Optional configuration overrides for the extensibility service connection.

    The backend service URL and credentials are resolved automatically
    from the Destination Service binding -- injected via ``app.yaml``.
    The SDK communicates with UMS via GraphQL; no
    URL patterns or manual setup needed.

    This config holds **optional overrides only**.  The required
    ``agent_ord_id`` is passed directly to :func:`create_client`.

    Attributes:
        destination_name: Optional override for the UMS destination name.
            When set, it is used directly, bypassing automatic resolution.
            When ``None`` (the default), the destination name is constructed as
            ``sap-managed-runtime-ias-{APPFND_CONHOS_LANDSCAPE}`` (requires
            ``APPFND_CONHOS_UMS_URL`` to be set).
        destination_instance: Destination service instance name. When ``"default"``,
            resolves to the default destination service instance. Specify a name
            only if your deployment binds the destination service under a
            non-default instance name.
    """

    destination_name: Optional[str] = None
    destination_instance: str = "default"
