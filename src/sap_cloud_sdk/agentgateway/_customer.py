"""Customer agent flow - file-based credentials with mTLS authentication.

Customer agents read credentials from a file mounted on the pod filesystem (STANDARD mode)
or from environment variables (TRANSPARENT mode).

Authentication flow (STANDARD mode):
- Tool discovery: mTLS client credentials → system-scoped token
- Tool invocation: mTLS + jwt-bearer grant → user-scoped token (principal propagation)

Authentication flow (TRANSPARENT mode):
- Tool discovery: client credentials (no mTLS) → system-scoped token
- Tool invocation: client credentials + jwt-bearer grant → user-scoped token
- Gateway handles mTLS externally, SDK uses standard HTTPS
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

from sap_cloud_sdk.agentgateway._dependencies_resolver import (
    EnvironmentDependenciesResolver,
    IntegrationDependenciesResolver,
)
from sap_cloud_sdk.agentgateway._models import (
    CustomerCredentials,
    IntegrationDependency,
    MCPTool,
)
from sap_cloud_sdk.agentgateway._token_cache import _TokenCache
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError
from sap_cloud_sdk.core.secret_resolver import resolve_base_mount

logger = logging.getLogger(__name__)

# servicebinding.io: scan $SERVICE_BINDING_ROOT for a binding whose 'type' file equals the expected type
_BINDING_TYPE = "integration-credentials"
_BINDING_TYPE_FILE = "type"
_CREDENTIALS_FILE = "credentials"

# Kyma default when SERVICE_BINDING_ROOT is not set
_DEFAULT_BINDING_ROOT = "/bindings"

# Environment variables for transparent mode
_INTEGRATION_CLIENT_ID_ENV = "INTEGRATION_CLIENT_ID"
_INTEGRATION_AUTH_URL_ENV = "INTEGRATION_AUTH_URL"
_INTEGRATION_GATEWAY_URL_ENV = "INTEGRATION_GATEWAY_URL"

# Resource URN for Agent Gateway token scope (hardcoded - production value)
_AGW_RESOURCE_URN = "urn:sap:identity:application:provider:name:agent-gateway"

# OAuth2 grant types
_GRANT_TYPE_CLIENT_CREDENTIALS = "client_credentials"
_GRANT_TYPE_JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"

# Token response field keys
_TOKEN_FIELD_CLIENT_ID = "client_id"
_TOKEN_FIELD_ACCESS_TOKEN = "access_token"


def _cache_scope_key(credentials: CustomerCredentials) -> str:
    """Build a cache scope key for customer-flow tokens."""
    return f"customer::{credentials.client_id}"


class _CredentialFields:
    """Field names in the credentials JSON file."""

    TOKEN_SERVICE_URL = "tokenServiceUrl"
    CLIENT_ID = "clientid"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "privateKey"
    GATEWAY_URL = "gatewayUrl"
    INTEGRATION_DEPENDENCIES = "integrationDependencies"
    ORD_ID = "ordId"
    GLOBAL_TENANT_ID = "globalTenantId"


def detect_customer_agent_credentials() -> str | None:
    """Check if customer agent credentials file exists.

    $SERVICE_BINDING_ROOT (or /bindings if unset): scans all subdirectories for one whose
       'type' file contains 'integration-credentials', then reads 'credentials' from that directory

    Returns:
        Path to credentials file if found, None otherwise.
    """

    # servicebinding.io: scan $SERVICE_BINDING_ROOT for a binding whose 'type' file equals _BINDING_TYPE
    sbr = resolve_base_mount(_DEFAULT_BINDING_ROOT)
    if sbr and os.path.isdir(sbr):
        for entry in os.scandir(sbr):
            if not entry.is_dir():
                continue
            type_file = os.path.join(entry.path, _BINDING_TYPE_FILE)
            if not os.path.isfile(type_file):
                continue
            with open(type_file) as f:
                if f.read().strip() != _BINDING_TYPE:
                    continue
            credentials_path = os.path.join(entry.path, _CREDENTIALS_FILE)
            if os.path.isfile(credentials_path):
                logger.debug(
                    "Customer credentials found via servicebinding.io type scan: %s",
                    credentials_path,
                )
                return credentials_path

    return None


def detect_transparent_credentials() -> bool:
    """Check if transparent mode environment variables are present.

    Checks for required environment variables:
    - INTEGRATION_CLIENT_ID
    - INTEGRATION_AUTH_URL
    - INTEGRATION_GATEWAY_URL

    Returns:
        True if all required environment variables are present, False otherwise.
    """
    has_client_id = bool(os.environ.get(_INTEGRATION_CLIENT_ID_ENV))
    has_auth_url = bool(os.environ.get(_INTEGRATION_AUTH_URL_ENV))
    has_gateway_url = bool(os.environ.get(_INTEGRATION_GATEWAY_URL_ENV))
    return has_client_id and has_auth_url and has_gateway_url


def load_customer_credentials_from_env(
    dependencies_resolver: IntegrationDependenciesResolver | None = None,
) -> CustomerCredentials:
    """Load customer credentials from environment variables (transparent mode).

    Args:
        dependencies_resolver: Optional custom resolver for integration dependencies.
            If None, uses EnvironmentDependenciesResolver (INTEGRATION_DEPENDENCIES env var).

    Returns:
        CustomerCredentials configured for transparent mode.

    Raises:
        AgentGatewaySDKError: If required environment variables are missing or invalid.
    """
    logger.info("using transparent mode")

    # Check required environment variables
    required_vars = {
        _INTEGRATION_CLIENT_ID_ENV: _TOKEN_FIELD_CLIENT_ID,
        _INTEGRATION_AUTH_URL_ENV: "auth_url",
        _INTEGRATION_GATEWAY_URL_ENV: "gateway_url",
    }

    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise AgentGatewaySDKError(
            f"Transparent TLS mode requires environment variables: {', '.join(missing)}"
        )

    client_id = os.environ[_INTEGRATION_CLIENT_ID_ENV]
    token_service_url = os.environ[_INTEGRATION_AUTH_URL_ENV]
    gateway_url = os.environ[_INTEGRATION_GATEWAY_URL_ENV].rstrip("/")

    # Resolve integration dependencies
    resolver = dependencies_resolver or EnvironmentDependenciesResolver()
    integration_dependencies = resolver.resolve()

    return CustomerCredentials(
        token_service_url=token_service_url,
        client_id=client_id,
        gateway_url=gateway_url,
        integration_dependencies=integration_dependencies,
        certificate=None,
        private_key=None,
    )


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
        _CredentialFields.CLIENT_ID: _TOKEN_FIELD_CLIENT_ID,
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
            'Expected format: [{"ordId": "...", "globalTenantId": "..."}]'
        )

    try:
        integration_deps = [
            IntegrationDependency(
                ord_id=dep[_CredentialFields.ORD_ID],
                global_tenant_id=dep[_CredentialFields.GLOBAL_TENANT_ID],
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
            'Expected format: [{"ordId": "...", "globalTenantId": "..."}]'
        )

    return CustomerCredentials(
        token_service_url=data[_CredentialFields.TOKEN_SERVICE_URL],
        client_id=data[_CredentialFields.CLIENT_ID],
        gateway_url=data[_CredentialFields.GATEWAY_URL].rstrip("/"),
        integration_dependencies=integration_deps,
        certificate=data[_CredentialFields.CERTIFICATE],
        private_key=data[_CredentialFields.PRIVATE_KEY],
    )


def _create_ssl_context(certificate: str, private_key: str) -> ssl.SSLContext:
    """Create SSL context for mTLS from in-memory certificate and key.

    Only used in STANDARD mode with file-based credentials.
    In TRANSPARENT mode, standard HTTPS is used without custom SSL context.

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


def _request_token_mtls(
    credentials: CustomerCredentials,
    grant_type: str,
    timeout: float,
    extra_data: dict | None = None,
) -> dict:
    """Make mTLS token request to IAS.

    Args:
        credentials: Customer credentials with certificate and private key.
        grant_type: OAuth2 grant type.
        timeout: HTTP timeout in seconds.
        extra_data: Additional form data for the token request.

    Returns:
        Token response payload.

    Raises:
        AgentGatewaySDKError: If token request fails.
    """
    if not credentials.certificate or not credentials.private_key:
        raise AgentGatewaySDKError(
            "Certificate and private key are required for mTLS token request."
        )
    ssl_context = _create_ssl_context(credentials.certificate, credentials.private_key)

    data = {
        _TOKEN_FIELD_CLIENT_ID: credentials.client_id,
        "grant_type": grant_type,
        "resource": _AGW_RESOURCE_URN,
    }

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
        access_token = token_data.get(_TOKEN_FIELD_ACCESS_TOKEN)

        if not access_token:
            raise AgentGatewaySDKError(
                f"Token response missing 'access_token'. Keys: {list(token_data.keys())}"
            )

        logger.debug("Token acquired successfully (length: %d)", len(access_token))
        return token_data

    except httpx.RequestError as e:
        raise AgentGatewaySDKError(f"Token request failed: {e}") from e


def _request_token_transparent(
    credentials: CustomerCredentials,
    grant_type: str,
    timeout: float,
    extra_data: dict | None = None,
) -> dict:
    """Make standard HTTPS token request without mTLS (transparent mode).

    Used in transparent mode where the gateway handles mTLS externally.
    The SDK makes a standard HTTPS request without client certificates.

    Args:
        credentials: Customer credentials (certificate and private_key should be None).
        grant_type: OAuth2 grant type.
        timeout: HTTP timeout in seconds.
        extra_data: Additional form data for the token request.

    Returns:
        Token response payload.

    Raises:
        AgentGatewaySDKError: If token request fails.
    """
    data = {
        _TOKEN_FIELD_CLIENT_ID: credentials.client_id,
        "grant_type": grant_type,
        "resource": _AGW_RESOURCE_URN,
    }

    if extra_data:
        data.update(extra_data)

    logger.debug(
        "Requesting token from %s with grant_type=%s (transparent mode)",
        credentials.token_service_url,
        grant_type,
    )

    try:
        with httpx.Client(timeout=timeout) as client:
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
        access_token = token_data.get(_TOKEN_FIELD_ACCESS_TOKEN)

        if not access_token:
            raise AgentGatewaySDKError(
                f"Token response missing 'access_token'. Keys: {list(token_data.keys())}"
            )

        logger.debug("Token acquired successfully (length: %d)", len(access_token))
        return token_data

    except httpx.RequestError as e:
        raise AgentGatewaySDKError(f"Token request failed: {e}") from e


def get_system_token_mtls(
    credentials: CustomerCredentials,
    timeout: float,
    token_cache: _TokenCache | None = None,
) -> str:
    """Get system-scoped token using client credentials flow.

    Automatically selects authentication mode based on credentials:
    - STANDARD mode: Uses mTLS with certificate and private key
    - TRANSPARENT mode: Uses standard HTTPS (gateway handles mTLS)

    Used for tool discovery where user identity is not needed.

    Args:
        credentials: Customer credentials.
        timeout: HTTP timeout in seconds.
        token_cache: Optional token cache used to reuse still-valid tokens.

    Returns:
        System-scoped access token, fetched or served from cache.
    """
    scope_key = _cache_scope_key(credentials)
    if token_cache:
        cached_token = token_cache.get_system_token(scope_key)
        if cached_token:
            logger.debug("Using cached system token for scope '%s'", scope_key)
            return cached_token

    # Determine which token request method to use based on credentials
    if credentials.certificate and credentials.private_key:
        # STANDARD mode: mTLS authentication
        logger.info("Acquiring system token via mTLS client credentials")
        token_data = _request_token_mtls(
            credentials,
            grant_type=_GRANT_TYPE_CLIENT_CREDENTIALS,
            timeout=timeout,
            extra_data={"response_type": "token"},
        )
    else:
        # TRANSPARENT mode: standard HTTPS authentication
        logger.info("Acquiring system token via transparent client credentials")
        token_data = _request_token_transparent(
            credentials,
            grant_type=_GRANT_TYPE_CLIENT_CREDENTIALS,
            timeout=timeout,
            extra_data={"response_type": "token"},
        )

    access_token = token_data[_TOKEN_FIELD_ACCESS_TOKEN]

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
    token_cache: _TokenCache | None = None,
) -> str:
    """Exchange user token for AGW-scoped token using jwt-bearer grant.

    Automatically selects authentication mode based on credentials:
    - STANDARD mode: Uses mTLS with certificate and private key
    - TRANSPARENT mode: Uses standard HTTPS (gateway handles mTLS)

    Used for tool invocation where user identity must be preserved
    for principal propagation.

    Args:
        credentials: Customer credentials.
        user_token: User's JWT token to exchange.
        timeout: HTTP timeout in seconds.
        token_cache: Optional token cache used to reuse still-valid exchanged
            tokens.

    Returns:
        AGW-scoped access token with user identity, fetched or served from cache.
    """
    scope_key = _cache_scope_key(credentials)
    if token_cache:
        cached_token = token_cache.get_user_token(user_token, scope_key)
        if cached_token:
            logger.debug("Using cached exchanged user token for scope '%s'", scope_key)
            return cached_token

    # Determine which token request method to use based on credentials
    if credentials.certificate and credentials.private_key:
        # STANDARD mode: mTLS authentication
        logger.info("Exchanging user token for AGW-scoped token via jwt-bearer grant")
        token_data = _request_token_mtls(
            credentials,
            grant_type=_GRANT_TYPE_JWT_BEARER,
            timeout=timeout,
            extra_data={
                "assertion": user_token,
                "token_format": "jwt",
            },
        )
    else:
        # TRANSPARENT mode: standard HTTPS authentication
        logger.info(
            "Exchanging user token for AGW-scoped token via transparent jwt-bearer grant"
        )
        token_data = _request_token_transparent(
            credentials,
            grant_type=_GRANT_TYPE_JWT_BEARER,
            timeout=timeout,
            extra_data={
                "assertion": user_token,
                "token_format": "jwt",
            },
        )

    access_token = token_data[_TOKEN_FIELD_ACCESS_TOKEN]

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
    """
    dependencies = credentials.integration_dependencies

    if not dependencies:
        logger.debug("integrationDependencies is empty in credentials — no MCP servers configured.")
        return []

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
            server_tools = await _list_server_tools(url, system_token, timeout)
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
