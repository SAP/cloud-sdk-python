"""URL validation helpers for the Agent Gateway module.

These guard the MCP tool-invocation path against bearer-token exfiltration:
the authenticated ``httpx`` client attaches a user/system-scoped token as a
connection-wide header, so the destination URL must be pinned to the trusted
gateway origin *before* that client is built. Any off-origin or non-HTTPS
destination is rejected here, so a poisoned tool/fragment URL can never
redirect the token to an attacker-controlled host.
"""

import re
from urllib.parse import urlparse

from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError

# ORD IDs and global tenant IDs are interpolated into the MCP URL path. They
# legitimately contain dots and colons (e.g. "sap.mcpbuilder:apiResource:cost-center:v1"
# or a UUID), so the stricter DMS id pattern cannot be reused. This allow-list
# still forbids every URL path metacharacter — "/", "\", "?", "#", "%", "@",
# whitespace — so a value can neither add path segments nor alter the origin.
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


def _validate_mcp_id(value: str, param_name: str) -> str:
    """Validate an ID that is interpolated into the MCP URL path.

    Args:
        value: The ``ord_id`` or ``global_tenant_id`` value.
        param_name: Name of the parameter, used in the error message.

    Returns:
        The validated value, unchanged (the gateway routes on the raw ``:``/``.``
        characters, so the value is not percent-encoded).

    Raises:
        AgentGatewaySDKError: If *value* is empty/whitespace, contains a URL path
            metacharacter, or is a ``.``/``..`` traversal segment.
    """
    if not value or not value.strip():
        raise AgentGatewaySDKError(f"{param_name} must not be empty")
    if value in (".", ".."):
        raise AgentGatewaySDKError(
            f"{param_name} must not be a path traversal segment: {value!r}"
        )
    if not _SAFE_ID_RE.match(value):
        raise AgentGatewaySDKError(
            f"{param_name} contains characters not allowed in a URL path segment: {value!r}"
        )
    return value


def _origin_host(parsed_host: str | None, parsed_port: int | None) -> str:
    """Render a ``host[:port]`` key for comparison (host lower-cased)."""
    host = (parsed_host or "").lower()
    return f"{host}:{parsed_port}" if parsed_port is not None else host


def _require_same_origin(
    url: str,
    allowed_origin: str,
    *,
    extra_allowed_hosts: tuple[str, ...] = (),
) -> None:
    """Pin an MCP destination URL to the trusted gateway origin.

    Call this before building the authenticated ``httpx`` client, so the bearer
    token is never attached to a request bound for an untrusted host.

    Args:
        url: The MCP tool/fragment destination URL to validate.
        allowed_origin: The trusted gateway base URL (from ``AuthResult``/
            credentials). Its host (and port) define the permitted origin.
        extra_allowed_hosts: Additional ``host`` or ``host:port`` values that are
            also permitted (the LoB escape hatch from ``ClientConfig``). Matching
            is case-insensitive.

    Raises:
        AgentGatewaySDKError: If *url* is not HTTPS, embeds credentials
            (userinfo), or its host does not match the allowed origin or an
            allow-listed host.
    """
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise AgentGatewaySDKError(
            f"MCP tool URL must use https, got scheme {parsed.scheme!r} in {url!r}"
        )

    if parsed.username or parsed.password:
        raise AgentGatewaySDKError("MCP tool URL must not embed credentials (userinfo)")

    url_host = _origin_host(parsed.hostname, parsed.port)
    if not url_host:
        raise AgentGatewaySDKError(f"MCP tool URL has no host: {url!r}")

    origin_parsed = urlparse(allowed_origin)
    origin_host = _origin_host(origin_parsed.hostname, origin_parsed.port)

    allowed = {origin_host} | {h.lower() for h in extra_allowed_hosts}
    if url_host not in allowed:
        raise AgentGatewaySDKError(
            f"MCP tool URL host {url_host!r} is not the trusted gateway origin "
            f"{origin_host!r}"
        )
