"""Customer agent flow - file-based credentials with mTLS authentication.

Customer agents read credentials from a file mounted on the pod filesystem.
This flow is used when credential files are detected.

Authentication flow:
- Tool discovery: mTLS client credentials → system-scoped token
- Tool invocation: mTLS + jwt-bearer grant → user-scoped token (principal propagation)
"""

import asyncio
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
from sap_cloud_sdk.agentgateway.exceptions import AgentGatewaySDKError

logger = logging.getLogger(__name__)

# Environment variable to override default credential path
_CREDENTIALS_PATH_ENV = "AGW_CREDENTIALS_PATH"

# Default credential path for Kyma production deployments
_CREDENTIALS_DEFAULT_PATH = "/etc/ums/credentials/credentials"

# HTTP timeout for token requests and MCP server calls (seconds)
_HTTP_TIMEOUT = 30.0

# Resource URN for Agent Gateway token scope (hardcoded - production value)
_AGW_RESOURCE_URN = "urn:sap:identity:application:provider:name:agent-gateway"

# OAuth2 grant types
_GRANT_TYPE_CLIENT_CREDENTIALS = "client_credentials"
_GRANT_TYPE_JWT_BEARER = "urn:ietf:params:oauth:grant-type:jwt-bearer"


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


def detect_customer_agent_credentials() -> str | None:
    """Check if customer agent credentials file exists.

    Checks for credential file in the following order:
    1. Path specified in AGW_CREDENTIALS_PATH env var
    2. Default mounted path: /etc/ums/credentials/credentials

    Returns:
        Path to credentials file if found, None otherwise.
    """
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


def _request_token_mtls(
    credentials: CustomerCredentials,
    grant_type: str,
    app_tid: str | None = None,
    extra_data: dict | None = None,
) -> str:
    """Make mTLS token request to IAS.

    Args:
        credentials: Customer credentials with certificate and private key.
        grant_type: OAuth2 grant type.
        app_tid: BTP Application Tenant ID of subscriber (optional).
        extra_data: Additional form data for the token request.

    Returns:
        Access token string.

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
            timeout=_HTTP_TIMEOUT,
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
        return access_token

    except httpx.RequestError as e:
        raise AgentGatewaySDKError(f"Token request failed: {e}")


def get_system_token_mtls(
    credentials: CustomerCredentials,
    app_tid: str | None = None,
) -> str:
    """Get system-scoped token using mTLS client credentials flow.

    Used for tool discovery where user identity is not needed.

    Args:
        credentials: Customer credentials.
        app_tid: BTP Application Tenant ID of subscriber (optional).

    Returns:
        System-scoped access token.
    """
    logger.info("Acquiring system token via mTLS client credentials")
    return _request_token_mtls(
        credentials,
        grant_type=_GRANT_TYPE_CLIENT_CREDENTIALS,
        app_tid=app_tid,
        extra_data={"response_type": "token"},
    )


def exchange_user_token(
    credentials: CustomerCredentials,
    user_token: str,
    app_tid: str | None = None,
) -> str:
    """Exchange user token for AGW-scoped token using jwt-bearer grant.

    Used for tool invocation where user identity must be preserved
    for principal propagation.

    Args:
        credentials: Customer credentials.
        user_token: User's JWT token to exchange.
        app_tid: BTP Application Tenant ID of subscriber (optional).

    Returns:
        AGW-scoped access token with user identity.
    """
    logger.info("Exchanging user token for AGW-scoped token via jwt-bearer grant")
    return _request_token_mtls(
        credentials,
        grant_type=_GRANT_TYPE_JWT_BEARER,
        app_tid=app_tid,
        extra_data={
            "assertion": user_token,
            "token_format": "jwt",
        },
    )


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
        timeout=_HTTP_TIMEOUT,
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
    app_tid: str | None = None,
) -> list[MCPTool]:
    """List all MCP tools from servers defined in credentials.

    Iterates over all integrationDependencies in the credentials file and
    discovers tools from each MCP server using mTLS client credentials.

    Args:
        credentials: Customer credentials with integrationDependencies.
        app_tid: BTP Application Tenant ID of subscriber (optional).

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

    # Get system token for discovery
    loop = asyncio.get_running_loop()
    system_token = await loop.run_in_executor(
        None, get_system_token_mtls, credentials, app_tid
    )

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
            server_tools = await _list_server_tools(url, system_token, dep)
            tools.extend(server_tools)
            logger.debug("Loaded %d tool(s) from %s", len(server_tools), dep.ord_id)
        except Exception:
            logger.exception("Failed to load tools from %s — skipping", dep.ord_id)

    logger.info(
        "Loaded %d MCP tool(s) from %d server(s)", len(tools), len(dependencies)
    )
    return tools


async def call_mcp_tool_customer(
    credentials: CustomerCredentials,
    tool: MCPTool,
    user_token: str | None,
    app_tid: str | None = None,
    **kwargs,
) -> str:
    """Invoke an MCP tool using customer flow.

    If user_token is provided, exchanges it for an AGW-scoped token to preserve
    user identity for principal propagation. Otherwise, falls back to system token.

    Args:
        credentials: Customer credentials.
        tool: MCPTool to invoke.
        user_token: User's JWT token for principal propagation (optional).
            If None, system token is used instead (no principal propagation).
        app_tid: BTP Application Tenant ID of subscriber (optional).
        **kwargs: Tool input parameters.

    Returns:
        Tool execution result as string.
    """
    logger.info("Calling tool '%s' on server '%s'", tool.name, tool.server_name)

    loop = asyncio.get_running_loop()

    if user_token:
        # Exchange user token for AGW-scoped token (with principal propagation)
        agw_token = await loop.run_in_executor(
            None, exchange_user_token, credentials, user_token, app_tid
        )
    else:
        # TODO: IBD workaround - use system token when user_token is not available.
        # This bypasses principal propagation. Remove this fallback once IBD
        # supports proper user token flow.
        logger.warning(
            "No user_token provided - using system token for tool invocation. "
            "Principal propagation will NOT work."
        )
        agw_token = await loop.run_in_executor(
            None, get_system_token_mtls, credentials, app_tid
        )

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {agw_token}",
            "x-correlation-id": str(uuid.uuid4()),
        },
        timeout=_HTTP_TIMEOUT,
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
