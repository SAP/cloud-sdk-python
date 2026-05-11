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
            When ``None`` (the default), the destination name is resolved
            automatically in order:
            (1) ``APPFND_UMS_DESTINATION_NAME`` environment variable,
            (2) ``sap-managed-runtime-ums-{APPFND_CONHOS_LANDSCAPE}``,
            (3) fallback to ``"EXTENSIBILITY_SERVICE"`` with a warning.
            Set this only when the destination follows a non-standard
            naming convention that cannot be expressed via environment
            variables.
        destination_instance: Destination service instance name. When ``"default"``,
            resolves to the default destination service instance. Specify a name
            only if your deployment binds the destination service under a
            non-default instance name.
    """

    destination_name: Optional[str] = None
    destination_instance: str = "default"


@dataclass
class HookConfig:
    """Configuration for calling hooks.

    Attributes:
        endpoint: Full URL of the hook endpoint to call including MCP ORD ID, GTID, and any path segments (e.g. ``"https://gateway.example.com/v1/mcp/{ORD_ID}/{GTID}"``).
        auth_token: Optional bearer token for authenticating against the hook endpoint.
        payload: Optional dictionary to send as JSON payload in the hook request.
        headers: Optional additional HTTP headers to include in the hook request.
    """

    endpoint: str
    auth_token: Optional[str] = None
    payload: Optional[dict] = None
    headers: Optional[dict] = None
