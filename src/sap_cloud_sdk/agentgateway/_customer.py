"""Customer agent flow - file-based credentials with mTLS authentication.

Customer agents read credentials from a file mounted on the pod filesystem.
This flow is used when credential files are detected.

In transparent TLS mode (TlsMode.TRANSPARENT) the OpenShell Gateway handles
the mTLS handshake and credential injection. The agent reads only endpoint URLs
from environment variables and never loads certificate or private key material.

Authentication flow:
- Standard mode: mTLS client credentials → system-scoped token
- Transparent mode: plain HTTPS (gateway-injected mTLS) → system-scoped token
- Tool invocation: jwt-bearer grant → user-scoped token (principal propagation)
"""

import json
import logging
import os
import ssl
import tempfile
import uuid

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from sap_cloud_sdk.agentgateway._models import (
    CustomerCredentials,
    IntegrationDependency,
    MCPTool,
)
from sap_cloud_sdk.agentgateway._token_cache import _TokenCache
from sap_cloud_sdk.agentgateway.config import TlsMode
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError

logger = logging.getLogger(__name__)

# Environment variable to override default credential path
_CREDENTIALS_PATH_ENV = "AGW_CREDENTIALS_PATH"

# Default credential path for Kyma production deployments
_CREDENTIALS_DEFAULT_PATH = "/etc/ums/credentials/credentials"

# Resource URN for Agent Gateway token scope (hardcoded - production value)
_AGW_RESOURCE_URN = "urn:sap:identity:application:provider:name:agent-gateway"

# OAuth2 grant types
_GRANT_TYPE_CLIENT_CREDENTIALS = "client_credentials"
_GRANT_TYPE_JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"

# Environment variables for transparent mode
_ENV_CLIENT_ID = "CLIENT_ID"
_ENV_TOKEN_SERVICE_URL = "TOKEN_SERVICE_URL"
_ENV_GATEWAY_URL = "GATEWAY_URL"
_ENV_INTEGRATION_DEPENDENCIES = "INTEGRATION_DEPENDENCIES"


def _cache_scope_key(credentials: CustomerCredentials, app_tid: str | None) -> str:
    """Build a cache scope key for customer-flow tokens."""
    return f"customer::{credentials.client_id}::{app_tid or ''}"


class _CredentialFields:
    """Field names in the credentials JSON file."""

    TOKEN_SERVICE_URL = "tokenServiceUrl"
    CLIENT_ID = "clientid"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "privateKey"
    GATEWAY_URL = "gatewayUrl"
    INTEGRATION_DEPENDENCIES = "integrationDependencies"
    ORD_ID = "ordId"
    DATA = "data"
    GLOBAL_TENANT_ID = "globalTenantId"


def detect_customer_agent_credentials(
    tls_mode: TlsMode = TlsMode.STANDARD,
) -> str | None:
    """Check if customer agent credentials file exists.

    In transparent mode the agent never uses a credentials file — the OpenShell
    Gateway injects certificates at the TLS layer and the agent reads only
    endpoint URLs from environment variables. Returns None immediately so the
    caller falls through to load_customer_credentials_from_env().

    In standard mode checks for a credential file in the following order:
    1. Path specified in AGW_CREDENTIALS_PATH env var
    2. Default mounted path: /etc/ums/credentials/credentials

    Args:
        tls_mode: TLS handling mode. When TRANSPARENT, skips file detection.

    Returns:
        Path to credentials file if found (standard mode only), None otherwise.
    """
    if tls_mode == TlsMode.TRANSPARENT:
        logger.debug("TLS_MODE=transparent: skipping credentials file detection")
        return None

    # Check env var first (path may be customized)
    path_from_env = os.environ.get(_CREDENTIALS_PATH_ENV)
    if path_from_env and os.path.isfile(path_from_env):
        logger.debug("Customer credentials found at env var path: %s", path_from_env)
        return path_from_env

    # Check default mounted path
    if os.path.isfile(_CREDENTIALS_DEFAULT_PATH):
        logger.debug(
            "Customer credentials found at default path: %s", _CREDENTIALS_DEFAULT_PATH
        )
        return _CREDENTIALS_DEFAULT_PATH

    return None


def load_customer_credentials(path: str) -> CustomerCredentials:
    """Load and parse customer credentials from file.

    Args:
        path: Path to the credentials JSON file.

    Returns:
        Parsed CustomerCredentials.

    Raises:
        AgentGatewaySDKError: If file cannot be read or is missing required fields.
    """
    logger.debug("Loading customer credentials from: %s", path)

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise AgentGatewaySDKError(f"Failed to load credentials from '{path}': {e}")

    # Map credential file keys to dataclass fields
    # Credential file uses camelCase, we use snake_case
    required_fields = {
        _CredentialFields.TOKEN_SERVICE_URL: "token_service_url",
        _CredentialFields.CLIENT_ID: "client_id",
        _CredentialFields.CERTIFICATE: "certificate",
        _CredentialFields.PRIVATE_KEY: "private_key",
        _CredentialFields.GATEWAY_URL: "gateway_url",
    }

    missing = [k for k in required_fields if k not in data]
    if missing:
        raise AgentGatewaySDKError(
            f"Credentials file missing required fields: {missing}"
        )

    # Parse integrationDependencies (required)
    if _CredentialFields.INTEGRATION_DEPENDENCIES not in data:
        raise AgentGatewaySDKError(
            "Credentials file missing required field: integrationDependencies. "
            'Expected format: [{"ordId": "...", "data": {"globalTenantId": "..."}}]'
        )

    try:
        integration_deps = [
            IntegrationDependency(
                ord_id=dep[_CredentialFields.ORD_ID],
                global_tenant_id=dep[_CredentialFields.DATA][
                    _CredentialFields.GLOBAL_TENANT_ID
                ],
            )
            for dep in data[_CredentialFields.INTEGRATION_DEPENDENCIES]
        ]
        logger.debug(
            "Loaded %d integration dependencies from credentials",
            len(integration_deps),
        )
    except (KeyError, TypeError) as e:
        raise AgentGatewaySDKError(
            f"Failed to parse integrationDependencies: {e}. "
            'Expected format: [{"ordId": "...", "data": {"globalTenantId": "..."}}]'
        )

    return CustomerCredentials(
        token_service_url=data[_CredentialFields.TOKEN_SERVICE_URL],
        client_id=data[_CredentialFields.CLIENT_ID],
        certificate=data[_CredentialFields.CERTIFICATE],
        private_key=data[_CredentialFields.PRIVATE_KEY],
        gateway_url=data[_CredentialFields.GATEWAY_URL].rstrip("/"),
        integration_dependencies=integration_deps,
    )


def load_customer_credentials_from_env() -> CustomerCredentials:
    """Load customer credentials from environment variables (transparent mode).

    Used when TlsMode.TRANSPARENT is active and the OpenShell Gateway handles
    mTLS. Certificate and private key are not required — they are injected at
    the TLS layer by the gateway.

    Environment variables:
        CLIENT_ID: IAS client ID (may be a gateway-resolved placeholder at runtime)
        TOKEN_SERVICE_URL: IAS token service endpoint
        GATEWAY_URL: Agent Gateway base URL
        INTEGRATION_DEPENDENCIES: JSON array of {ordId, globalTenantId} objects

    Returns:
        CustomerCredentials with certificate and private_key set to None.

    Raises:
        AgentGatewaySDKError: If required environment variables are missing or
            INTEGRATION_DEPENDENCIES cannot be parsed.
    """
    required = [_ENV_CLIENT_ID, _ENV_TOKEN_SERVICE_URL, _ENV_GATEWAY_URL]
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise AgentGatewaySDKError(
            f"TLS_MODE=transparent requires environment variables: {missing}"
        )

    raw_deps = os.environ.get(_ENV_INTEGRATION_DEPENDENCIES, "[]")
    try:
        deps_data = json.loads(raw_deps)
        integration_dependencies = [
            IntegrationDependency(
                ord_id=dep[_CredentialFields.ORD_ID],
                global_tenant_id=dep[_CredentialFields.GLOBAL_TENANT_ID],
            )
            for dep in deps_data
        ]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise AgentGatewaySDKError(
            f"Failed to parse INTEGRATION_DEPENDENCIES: {e}. "
            'Expected format: [{"ordId": "...", "globalTenantId": "..."}]'
        )

    logger.debug(
        "Loaded %d integration dependencies from environment", len(integration_dependencies)
    )

    return CustomerCredentials(
        token_service_url=os.environ[_ENV_TOKEN_SERVICE_URL],
        client_id=os.environ[_ENV_CLIENT_ID],
        certificate=None,
        private_key=None,
        gateway_url=os.environ[_ENV_GATEWAY_URL].rstrip("/"),
        integration_dependencies=integration_dependencies,
    )


def _create_ssl_context(certificate: str, private_key: str) -> ssl.SSLContext:
    """Create SSL context for mTLS from in-memory certificate and key.

    Uses temporary files as a bridge since ssl.SSLContext requires file paths
    or loaded certificate objects. The files are created with secure permissions
    and cleaned up immediately after loading.

    Note: While httpx supports passing cert as a tuple of file paths, it doesn't
    directly support in-memory certificates. Using temporary files is the most
    compatible approach across different SSL backends.

    Args:
        certificate: PEM-encoded certificate string.
        private_key: PEM-encoded private key string.

    Returns:
        Configured SSL context for mTLS.

    Raises:
        AgentGatewaySDKError: If SSL context creation fails.
    """
    cert_file = None
    key_file = None

    try:
        # Create temporary files with secure permissions (readable only by owner)
        cert_file = tempfile.NamedTemporaryFile(mode="w", suffix=".crt", delete=False)
        key_file = tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False)

        cert_file.write(certificate)
        cert_file.close()
        key_file.write(private_key)
        key_file.close()

        # Create SSL context and load the certificate/key
        ssl_context = ssl.create_default_context()
        ssl_context.load_cert_chain(cert_file.name, key_file.name)

        return ssl_context

    except ssl.SSLError as e:
        raise AgentGatewaySDKError(f"Failed to create SSL context: {e}")

    finally:
        # Clean up temporary files
        if cert_file and os.path.exists(cert_file.name):
            os.unlink(cert_file.name)
        if key_file and os.path.exists(key_file.name):
            os.unlink(key_file.name)


def _create_http_client_transparent(timeout: float) -> httpx.Client:
    """Create an HTTP client for transparent TLS mode.

    The OpenShell Gateway handles TLS and mTLS on behalf of the agent, so no
    SSL context is configured. All HTTPS requests are routed through the proxy
    set in the HTTPS_PROXY environment variable.

    Args:
        timeout: HTTP timeout in seconds.

    Returns:
        httpx.Client without any custom SSL context.
    """
    return httpx.Client(timeout=timeout)


def _request_token_transparent(
    credentials: CustomerCredentials,
    grant_type: str,
    timeout: float,
    app_tid: str | None = None,
    extra_data: dict | None = None,
) -> dict:
    """Make a token request in transparent TLS mode.

    The OpenShell Gateway intercepts the HTTPS connection and:
    1. Injects the client certificate at the TLS layer (mTLS handshake).
    2. Rewrites the client_id placeholder in the request body.

    The agent sends the OAuth2 POST body without loading any certificate or key.

    Args:
        credentials: Customer credentials (certificate/private_key are None).
        grant_type: OAuth2 grant type.
        timeout: HTTP timeout in seconds.
        app_tid: BTP Application Tenant ID of subscriber (optional).
        extra_data: Additional form data for the token request.

    Returns:
        Token response payload.

    Raises:
        AgentGatewaySDKError: If token request fails.
    """
    data: dict = {
        "client_id": credentials.client_id,
        "grant_type": grant_type,
        "resource": _AGW_RESOURCE_URN,
    }

    if app_tid:
        data["app_tid"] = app_tid

    if extra_data:
        data.update(extra_data)

    logger.debug(
        "Requesting token (transparent mode) from %s with grant_type=%s",
        credentials.token_service_url,
        grant_type,
    )

    try:
        with _create_http_client_transparent(timeout) as client:
            response = client.post(
                credentials.token_service_url,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            )

        if response.status_code != 200:
            logger.error(
                "Token request failed with status %d: %s",
                response.status_code,
                response.text[:500],
            )
            raise AgentGatewaySDKError(
                f"Token request failed with status {response.status_code}: {response.text[:200]}"
            )

        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise AgentGatewaySDKError(
                f"Token response missing 'access_token'. Keys: {list(token_data.keys())}"
            )

        logger.debug(
            "Token acquired successfully (transparent mode, length: %d)", len(access_token)
        )
        return token_data

    except httpx.RequestError as e:
        raise AgentGatewaySDKError(f"Token request failed: {e}")


def _request_token_mtls(
    credentials: CustomerCredentials,
    grant_type: str,
    timeout: float,
    app_tid: str | None = None,
    extra_data: dict | None = None,
) -> dict:
    """Make mTLS token request to IAS.

    Args:
        credentials: Customer credentials with certificate and private key.
        grant_type: OAuth2 grant type.
        timeout: HTTP timeout in seconds.
        app_tid: BTP Application Tenant ID of subscriber (optional).
        extra_data: Additional form data for the token request.

    Returns:
        Token response payload.

    Raises:
        AgentGatewaySDKError: If token request fails.
    """
    ssl_context = _create_ssl_context(credentials.certificate, credentials.private_key)

    data = {
        "client_id": credentials.client_id,
        "grant_type": grant_type,
        "resource": _AGW_RESOURCE_URN,
    }

    # TODO: app_tid requirement is still being clarified with the IBD team.
    # This parameter may be removed if it turns out to be unnecessary.
    if app_tid:
        data["app_tid"] = app_tid

    if extra_data:
        data.update(extra_data)

    logger.debug(
        "Requesting token from %s with grant_type=%s",
        credentials.token_service_url,
        grant_type,
    )

    try:
        with httpx.Client(
            verify=ssl_context,
            timeout=timeout,
        ) as client:
            response = client.post(
                credentials.token_service_url,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            )

        if response.status_code != 200:
            logger.error(
                "Token request failed with status %d: %s",
                response.status_code,
                response.text[:500],
            )
            raise AgentGatewaySDKError(
                f"Token request failed with status {response.status_code}: {response.text[:200]}"
            )

        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise AgentGatewaySDKError(
                f"Token response missing 'access_token'. Keys: {list(token_data.keys())}"
            )

        logger.debug("Token acquired successfully (length: %d)", len(access_token))
        return token_data

    except httpx.RequestError as e:
        raise AgentGatewaySDKError(f"Token request failed: {e}")


def get_system_token_mtls(
    credentials: CustomerCredentials,
    timeout: float,
    app_tid: str | None = None,
    token_cache: _TokenCache | None = None,
) -> str:
    """Get system-scoped token using mTLS client credentials flow.

    Used for tool discovery where user identity is not needed.

    Args:
        credentials: Customer credentials.
        timeout: HTTP timeout in seconds.
        app_tid: BTP Application Tenant ID of subscriber (optional).
        token_cache: Optional token cache used to reuse still-valid tokens.

    Returns:
        System-scoped access token, fetched or served from cache.
    """
    scope_key = _cache_scope_key(credentials, app_tid)
    if token_cache:
        cached_token = token_cache.get_system_token(scope_key)
        if cached_token:
            logger.debug("Using cached system token for scope '%s'", scope_key)
            return cached_token

    logger.info("Acquiring system token via mTLS client credentials")
    token_data = _request_token_mtls(
        credentials,
        grant_type=_GRANT_TYPE_CLIENT_CREDENTIALS,
        timeout=timeout,
        app_tid=app_tid,
        extra_data={"response_type": "token"},
    )
    access_token = token_data["access_token"]

    if token_cache:
        token_cache.set_system_token(
            access_token,
            token_cache.compute_expires_at(token_data),
            scope_key,
        )

    return access_token


def get_system_token_transparent(
    credentials: CustomerCredentials,
    timeout: float,
    app_tid: str | None = None,
    token_cache: _TokenCache | None = None,
) -> str:
    """Get system-scoped token in transparent TLS mode.

    Equivalent to get_system_token_mtls() but uses _request_token_transparent()
    so the agent never performs a TLS handshake directly.

    Args:
        credentials: Customer credentials loaded from environment variables.
        timeout: HTTP timeout in seconds.
        app_tid: BTP Application Tenant ID of subscriber (optional).
        token_cache: Optional token cache.

    Returns:
        System-scoped access token, fetched or served from cache.
    """
    scope_key = _cache_scope_key(credentials, app_tid)
    if token_cache:
        cached_token = token_cache.get_system_token(scope_key)
        if cached_token:
            logger.debug("Using cached system token for scope '%s'", scope_key)
            return cached_token

    logger.info("Acquiring system token via transparent mode (gateway-injected mTLS)")
    token_data = _request_token_transparent(
        credentials,
        grant_type=_GRANT_TYPE_CLIENT_CREDENTIALS,
        timeout=timeout,
        app_tid=app_tid,
        extra_data={"response_type": "token"},
    )
    access_token = token_data["access_token"]

    if token_cache:
        token_cache.set_system_token(
            access_token,
            token_cache.compute_expires_at(token_data),
            scope_key,
        )

    return access_token


def exchange_user_token(
    credentials: CustomerCredentials,
    user_token: str,
    timeout: float,
    app_tid: str | None = None,
    token_cache: _TokenCache | None = None,
) -> str:
    """Exchange user token for AGW-scoped token using jwt-bearer grant.

    Used for tool invocation where user identity must be preserved
    for principal propagation.

    Args:
        credentials: Customer credentials.
        user_token: User's JWT token to exchange.
        timeout: HTTP timeout in seconds.
        app_tid: BTP Application Tenant ID of subscriber (optional).
        token_cache: Optional token cache used to reuse still-valid exchanged
            tokens.

    Returns:
        AGW-scoped access token with user identity, fetched or served from cache.
    """
    scope_key = _cache_scope_key(credentials, app_tid)
    if token_cache:
        cached_token = token_cache.get_user_token(user_token, scope_key)
        if cached_token:
            logger.debug("Using cached exchanged user token for scope '%s'", scope_key)
            return cached_token

    logger.info("Exchanging user token for AGW-scoped token via jwt-bearer grant")
    token_data = _request_token_mtls(
        credentials,
        grant_type=_GRANT_TYPE_JWT_BEARER,
        timeout=timeout,
        app_tid=app_tid,
        extra_data={
            "assertion": user_token,
            "token_format": "jwt",
        },
    )
    access_token = token_data["access_token"]

    if token_cache:
        token_cache.set_user_token(
            user_token,
            access_token,
            token_cache.compute_expires_at(token_data),
            scope_key,
        )

    return access_token


def exchange_user_token_transparent(
    credentials: CustomerCredentials,
    user_token: str,
    timeout: float,
    app_tid: str | None = None,
    token_cache: _TokenCache | None = None,
) -> str:
    """Exchange user token for AGW-scoped token in transparent TLS mode.

    Equivalent to exchange_user_token() but uses _request_token_transparent()
    so the agent never performs a TLS handshake directly.

    Args:
        credentials: Customer credentials loaded from environment variables.
        user_token: User's JWT token to exchange.
        timeout: HTTP timeout in seconds.
        app_tid: BTP Application Tenant ID of subscriber (optional).
        token_cache: Optional token cache.

    Returns:
        AGW-scoped access token with user identity, fetched or served from cache.
    """
    scope_key = _cache_scope_key(credentials, app_tid)
    if token_cache:
        cached_token = token_cache.get_user_token(user_token, scope_key)
        if cached_token:
            logger.debug("Using cached exchanged user token for scope '%s'", scope_key)
            return cached_token

    logger.info(
        "Exchanging user token for AGW-scoped token via jwt-bearer grant (transparent mode)"
    )
    token_data = _request_token_transparent(
        credentials,
        grant_type=_GRANT_TYPE_JWT_BEARER,
        timeout=timeout,
        app_tid=app_tid,
        extra_data={
            "assertion": user_token,
            "token_format": "jwt",
        },
    )
    access_token = token_data["access_token"]

    if token_cache:
        token_cache.set_user_token(
            user_token,
            access_token,
            token_cache.compute_expires_at(token_data),
            scope_key,
        )

    return access_token


def _build_mcp_url(gateway_url: str, ord_id: str, gt_id: str) -> str:
    """Build MCP server URL from gateway URL, ord_id, and gt_id.

    URL format: {gateway_url}/v1/mcp/{ord_id}/{gt_id}

    If gateway_url already contains /v1/mcp, it is preserved.

    Args:
        gateway_url: Base gateway URL from credentials.
        ord_id: Open Resource Discovery ID of the MCP server.
        gt_id: Global Tenant ID (looked up from integrationDependencies).

    Returns:
        Full MCP server URL.
    """
    # Gateway URL may or may not include /v1/mcp
    if "/v1/mcp" in gateway_url:
        return f"{gateway_url}/{ord_id}/{gt_id}"
    else:
        return f"{gateway_url}/v1/mcp/{ord_id}/{gt_id}"


async def _list_server_tools(
    url: str,
    auth_token: str,
    dependency: IntegrationDependency,
    timeout: float,
) -> list[MCPTool]:
    """List tools from a single MCP server.

    Args:
        url: MCP server endpoint URL.
        auth_token: Authorization token.
        dependency: Integration dependency (for metadata).

    Returns:
        List of MCPTool objects from this server.

    Raises:
        AgentGatewaySDKError: If server does not provide serverInfo.name.
    """
    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {auth_token}",
            "x-correlation-id": str(uuid.uuid4()),
        },
        timeout=timeout,
    ) as http_client:
        async with streamable_http_client(url, http_client=http_client) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                init_result = await session.initialize()

                if not (
                    init_result
                    and init_result.serverInfo
                    and init_result.serverInfo.name
                ):
                    raise AgentGatewaySDKError(
                        f"MCP server at '{url}' did not provide serverInfo.name. "
                        "This is required by the MCP protocol."
                    )

                server_name = init_result.serverInfo.name
                result = await session.list_tools()

                return [
                    MCPTool(
                        name=t.name,
                        server_name=server_name,
                        description=t.description or "",
                        input_schema=t.inputSchema or {},
                        url=url,
                    )
                    for t in result.tools
                ]


async def get_mcp_tools_customer(
    credentials: CustomerCredentials,
    system_token: str,
    timeout: float,
) -> list[MCPTool]:
    """List all MCP tools from servers defined in credentials.

    Iterates over all integrationDependencies in the credentials file and
    discovers tools from each MCP server using a pre-fetched system token.

    Args:
        credentials: Customer credentials with integrationDependencies.
        system_token: Pre-fetched raw system token for authentication.
        timeout: HTTP timeout in seconds for MCP server calls.

    Returns:
        List of MCPTool objects from all servers.

    Raises:
        AgentGatewaySDKError: If integrationDependencies is empty.
    """
    dependencies = credentials.integration_dependencies

    if not dependencies:
        raise AgentGatewaySDKError(
            "integrationDependencies is empty in credentials — no MCP servers configured."
        )

    logger.info("Discovering tools from %d MCP server(s)", len(dependencies))

    tools: list[MCPTool] = []

    for dep in dependencies:
        url = _build_mcp_url(credentials.gateway_url, dep.ord_id, dep.global_tenant_id)
        logger.debug(
            "Discovering tools from %s (ord_id=%s, gt_id=%s)",
            url,
            dep.ord_id,
            dep.global_tenant_id,
        )

        try:
            server_tools = await _list_server_tools(url, system_token, dep, timeout)
            tools.extend(server_tools)
            logger.debug("Loaded %d tool(s) from %s", len(server_tools), dep.ord_id)
        except Exception:
            logger.exception("Failed to load tools from %s — skipping", dep.ord_id)

    logger.info(
        "Loaded %d MCP tool(s) from %d server(s)", len(tools), len(dependencies)
    )
    return tools


async def call_mcp_tool_customer(
    tool: MCPTool,
    auth_token: str,
    timeout: float,
    **kwargs,
) -> str:
    """Invoke an MCP tool using customer flow.

    Uses a pre-fetched token (either user-scoped or system-scoped) for
    authentication against the MCP server.

    Args:
        tool: MCPTool to invoke.
        auth_token: Pre-fetched raw access token for authentication.
        timeout: HTTP timeout in seconds for the MCP server call.
        **kwargs: Tool input parameters.

    Returns:
        Tool execution result as string.
    """
    logger.info("Calling tool '%s' on server '%s'", tool.name, tool.server_name)

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {auth_token}",
            "x-correlation-id": str(uuid.uuid4()),
        },
        timeout=timeout,
    ) as http_client:
        async with streamable_http_client(tool.url, http_client=http_client) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool.name, kwargs)

                if not result.content:
                    logger.warning("Tool '%s' returned empty content", tool.name)
                    return ""

                first = result.content[0]
                return str(getattr(first, "text", ""))
