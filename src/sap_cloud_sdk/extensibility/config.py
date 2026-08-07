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
            When set, the legacy flow is used exclusively: the base URL and
            mTLS certificate are read from this destination, bypassing the
            new IAS-based flow entirely.
            When ``None`` (the default), the new flow is attempted first
            (URL from ``APPFND_CONHOS_UMS_URL``, cert from the IAS
            destination ``sap-managed-runtime-ias-{APPFND_CONHOS_LANDSCAPE}``),
            falling back to the legacy UMS destination resolved via
            ``APPFND_UMS_DESTINATION_NAME`` or
            ``sap-managed-runtime-ums-{APPFND_CONHOS_LANDSCAPE}``.
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